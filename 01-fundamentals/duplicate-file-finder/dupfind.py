"""Find duplicate files: group by size, then by a hash of the first 4 KB, then by full SHA-256."""

import argparse
import csv
import fnmatch
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

PREFIX_SIZE = 4096
CHUNK_SIZE = 64 * 1024


def parse_size(text: str) -> int:
    """'500', '10K', '2M', '1G' -> bytes."""
    units = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
    text = text.strip().upper().removesuffix("B")
    if text and text[-1] in units:
        return int(float(text[:-1]) * units[text[-1]])
    return int(text)


def human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def is_excluded(relative: str, patterns: list) -> bool:
    name = relative.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(relative, p) or fnmatch.fnmatch(name, p) for p in patterns)


def collect_files(roots: list, min_size: int = 1, exclude: list = ()) -> list:
    """All regular files under the roots, as (path, size).

    Symlinks are skipped and each inode is counted once, so hard links and
    overlapping roots don't show up as duplicates.
    """
    seen = set()
    files = []
    for root in roots:
        for path in sorted(root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            if is_excluded(path.relative_to(root).as_posix(), exclude):
                continue
            try:
                info = path.stat()
            except OSError:
                continue
            if (info.st_dev, info.st_ino) in seen or info.st_size < min_size:
                continue
            seen.add((info.st_dev, info.st_ino))
            files.append((path, info.st_size))
    return files


def hash_file(path: Path, limit: int | None = None) -> str:
    """SHA-256 of the whole file, or of its first `limit` bytes."""
    digest = hashlib.sha256()
    remaining = limit
    with open(path, "rb") as fh:
        while remaining is None or remaining > 0:
            size = CHUNK_SIZE if remaining is None else min(CHUNK_SIZE, remaining)
            chunk = fh.read(size)
            if not chunk:
                break
            digest.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return digest.hexdigest()


def regroup(groups: list, key) -> list:
    """Split every group by key(path, size) and keep only sub-groups with 2+ files."""
    result = []
    for group in groups:
        buckets = defaultdict(list)
        for path, size in group:
            try:
                buckets[key(path, size)].append((path, size))
            except OSError as exc:
                print(f"warning: could not read {path}: {exc.strerror}", file=sys.stderr)
        result.extend(b for b in buckets.values() if len(b) > 1)
    return result


def count(groups: list) -> int:
    return sum(len(g) for g in groups)


def find_duplicates(files: list) -> tuple[list, list]:
    """Run the three stages. Returns (duplicate groups, per-stage stats)."""
    stats = []

    groups = regroup([files], lambda path, size: size)
    stats.append({"stage": "same size", "before": len(files), "after": count(groups),
                  "bytes_read": 0})

    before = count(groups)
    read = sum(min(size, PREFIX_SIZE) for g in groups for _, size in g)
    groups = regroup(groups, lambda path, size: hash_file(path, PREFIX_SIZE))
    stats.append({"stage": "first 4 KB", "before": before, "after": count(groups),
                  "bytes_read": read})

    before = count(groups)
    read = sum(size for g in groups for _, size in g)
    full_hashes = {}

    def full_key(path, size):
        full_hashes[path] = hash_file(path)
        return full_hashes[path]

    groups = regroup(groups, full_key)
    stats.append({"stage": "full SHA-256", "before": before, "after": count(groups),
                  "bytes_read": read})

    duplicates = [{"size": g[0][1], "sha256": full_hashes[g[0][0]],
                   "paths": sorted(str(p) for p, _ in g)} for g in groups]
    duplicates.sort(key=lambda d: d["size"] * (len(d["paths"]) - 1), reverse=True)
    return duplicates, stats


def wasted_space(duplicates: list) -> int:
    """Bytes that could be freed by keeping one copy of each group."""
    return sum(d["size"] * (len(d["paths"]) - 1) for d in duplicates)


def write_report(path: Path, duplicates: list) -> None:
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(duplicates, indent=2), encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["group", "size", "sha256", "path"])
        for i, d in enumerate(duplicates, 1):
            for p in d["paths"]:
                writer.writerow([i, d["size"], d["sha256"], p])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report duplicate files (same content). Never deletes anything.")
    parser.add_argument("folders", nargs="+", type=Path)
    parser.add_argument("--min-size", type=parse_size, default=1, metavar="SIZE",
                        help="ignore files smaller than this, e.g. 100, 10K, 1M (default 1 byte)")
    parser.add_argument("--exclude", action="append", default=[], metavar="PATTERN",
                        help="glob to ignore, e.g. '*.tmp' or 'cache/*' (repeatable)")
    parser.add_argument("--report", type=Path, metavar="FILE",
                        help="also write the groups to FILE (.csv or .json)")
    args = parser.parse_args()

    for folder in args.folders:
        if not folder.is_dir():
            print(f"error: {folder} is not a directory", file=sys.stderr)
            return 2
    if args.report and args.report.suffix.lower() not in (".csv", ".json"):
        print("error: --report must end in .csv or .json", file=sys.stderr)
        return 2

    start = time.perf_counter()
    files = collect_files(args.folders, args.min_size, args.exclude)
    duplicates, stats = find_duplicates(files)
    elapsed = time.perf_counter() - start

    total = sum(size for _, size in files)
    print(f"Scanned {len(files)} files ({human(total)}) in {len(args.folders)} folder(s)\n")
    for s in stats:
        print(f"  {s['stage']:<13} {s['before']:>6} -> {s['after']:<6} candidates "
              f"({s['before'] - s['after']} eliminated, {human(s['bytes_read'])} read)")
    staged = sum(s["bytes_read"] for s in stats)
    print(f"  read {human(staged)} in total; hashing every file would read {human(total)}")

    for i, d in enumerate(duplicates, 1):
        print(f"\nGroup {i}: {len(d['paths'])} copies of {human(d['size'])}  "
              f"sha256 {d['sha256'][:12]}")
        for p in d["paths"]:
            print(f"  {p}")

    extra = sum(len(d["paths"]) - 1 for d in duplicates)
    print(f"\n{len(duplicates)} group(s), {extra} redundant copies, "
          f"{human(wasted_space(duplicates))} wasted  ({elapsed:.2f}s)")

    if args.report:
        write_report(args.report, duplicates)
        print(f"Report written to {args.report}")
    return 1 if duplicates else 0


if __name__ == "__main__":
    sys.exit(main())
