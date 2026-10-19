"""Sort the files of a folder into subfolders by category or by date, with undo."""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

LOG_NAME = "organizer-log.json"

CATEGORIES = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic", ".tiff"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".md", ".odt", ".rtf", ".ppt", ".pptx"],
    "spreadsheets": [".xls", ".xlsx", ".csv", ".ods", ".tsv"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "code": [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".sh", ".json",
             ".sql", ".ipynb"],
}
OTHER = "other"


def load_categories(path: Path) -> dict:
    """Read {"folder": [".ext", ...]} from a JSON file and build an extension lookup."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not all(isinstance(v, list) for v in data.values()):
        raise ValueError('expected an object like {"images": [".jpg", ".png"]}')
    return data


def extension_map(categories: dict) -> dict:
    lookup = {}
    for folder, extensions in categories.items():
        for ext in extensions:
            ext = ext.lower()
            lookup[ext if ext.startswith(".") else "." + ext] = folder
    return lookup


def target_folder(path: Path, mode: str, ext_map: dict) -> str:
    if mode == "date":
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        return f"{modified:%Y}/{modified:%m}"
    return ext_map.get(path.suffix.lower(), OTHER)


def list_files(root: Path, recursive: bool) -> list:
    """Regular files to organise. Hidden files/folders and the move log are skipped."""
    candidates = root.rglob("*") if recursive else root.iterdir()
    files = []
    for path in candidates:
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_file() and not path.is_symlink() and path.name != LOG_NAME:
            files.append(path)
    return sorted(files)


def free_name(destination: Path, taken: set) -> Path:
    """Return destination, or 'name (1).ext', 'name (2).ext'... if it is already used."""
    candidate = destination
    n = 1
    while candidate.exists() or candidate in taken:
        candidate = destination.with_name(f"{destination.stem} ({n}){destination.suffix}")
        n += 1
    return candidate


def make_plan(root: Path, mode: str = "category", ext_map: dict | None = None,
              recursive: bool = False) -> list:
    """List of (source, destination) moves. Nothing is touched on disk."""
    ext_map = ext_map if ext_map is not None else extension_map(CATEGORIES)
    plan = []
    taken = set()
    for path in list_files(root, recursive):
        folder = root / target_folder(path, mode, ext_map)
        if path.parent == folder:
            continue    # already in the right place (recursive runs)
        destination = free_name(folder / path.name, taken)
        taken.add(destination)
        plan.append((path, destination))
    return plan


def read_log(root: Path) -> list:
    log_path = root / LOG_NAME
    if not log_path.exists():
        return []
    return json.loads(log_path.read_text(encoding="utf-8"))["runs"]


def write_log(root: Path, runs: list) -> None:
    log_path = root / LOG_NAME
    if runs:
        log_path.write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
    elif log_path.exists():
        log_path.unlink()


def apply_plan(root: Path, plan: list) -> dict:
    """Move the files and append the run to the log so it can be undone."""
    created_dirs = []
    moves = []
    for source, destination in plan:
        missing = []
        parent = destination.parent
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for folder in reversed(missing):
            folder.mkdir()
            created_dirs.append(folder.relative_to(root).as_posix())
        try:
            shutil.move(str(source), str(destination))
        except OSError as exc:
            print(f"warning: could not move {source.name}: {exc.strerror}", file=sys.stderr)
            continue
        moves.append({"from": source.relative_to(root).as_posix(),
                      "to": destination.relative_to(root).as_posix()})

    run = {"time": datetime.now().isoformat(timespec="seconds"),
           "moves": moves, "created_dirs": created_dirs}
    write_log(root, read_log(root) + [run])
    return run


def undo_last(root: Path) -> tuple[int, list]:
    """Move the files of the last run back. Returns (files restored, warnings)."""
    runs = read_log(root)
    if not runs:
        raise FileNotFoundError(f"no {LOG_NAME} with runs to undo in {root}")
    run = runs.pop()
    restored = 0
    warnings = []
    for move in reversed(run["moves"]):
        current, original = root / move["to"], root / move["from"]
        if not current.exists():
            warnings.append(f"missing, not restored: {move['to']}")
            continue
        if original.exists():
            warnings.append(f"{move['from']} exists again, left {move['to']} in place")
            continue
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(current), str(original))
        restored += 1

    # Remove the folders this run created, deepest first, but only if now empty.
    for folder in sorted(run["created_dirs"], key=lambda d: d.count("/"), reverse=True):
        path = root / folder
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()

    write_log(root, runs)
    return restored, warnings


def print_plan(root: Path, plan: list, dry_run: bool) -> None:
    for source, destination in plan:
        print(f"  {source.relative_to(root).as_posix():<34} -> "
              f"{destination.relative_to(root).as_posix()}")
    counts = {}
    for _, destination in plan:
        folder = destination.parent.relative_to(root).as_posix()
        counts[folder] = counts.get(folder, 0) + 1
    summary = ", ".join(f"{folder}: {n}" for folder, n in sorted(counts.items()))
    verb = "would move" if dry_run else "moved"
    print(f"\n{len(plan)} file(s) {verb}" + (f" ({summary})" if summary else ""))


def cmd_sort(args) -> int:
    ext_map = extension_map(CATEGORIES)
    if args.config:
        try:
            ext_map = extension_map(load_categories(args.config))
        except (OSError, ValueError) as exc:
            print(f"error: bad config {args.config}: {exc}", file=sys.stderr)
            return 2

    plan = make_plan(args.directory, args.by, ext_map, args.recursive)
    if not plan:
        print("Nothing to move.")
        return 0
    if args.dry_run:
        print("Dry run, nothing is moved:")
        print_plan(args.directory, plan, dry_run=True)
        return 0

    run = apply_plan(args.directory, plan)
    done = [(args.directory / m["from"], args.directory / m["to"]) for m in run["moves"]]
    print_plan(args.directory, done, dry_run=False)
    print(f"Log written to {args.directory / LOG_NAME}, run 'undo' to revert.")
    return 0


def cmd_undo(args) -> int:
    try:
        restored, warnings = undo_last(args.directory)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(f"Restored {restored} file(s) to their original place.")
    return 1 if warnings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Organise a messy folder into subfolders.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sort = sub.add_parser("sort", help="move files into subfolders")
    p_sort.add_argument("directory", type=Path)
    p_sort.add_argument("--by", choices=["category", "date"], default="category",
                        help="category = by extension, date = YYYY/MM of modification time")
    p_sort.add_argument("--config", type=Path,
                        help='JSON with your own categories: {"folder": [".ext", ...]}')
    p_sort.add_argument("--dry-run", action="store_true", help="show the plan, move nothing")
    p_sort.add_argument("--recursive", action="store_true", help="also take files from subfolders")
    p_sort.set_defaults(func=cmd_sort)

    p_undo = sub.add_parser("undo", help="revert the last sort of a directory")
    p_undo.add_argument("directory", type=Path)
    p_undo.set_defaults(func=cmd_undo)

    args = parser.parse_args()
    if not args.directory.is_dir():
        print(f"error: {args.directory} is not a directory", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
