# duplicate-file-finder — What it does

## In one sentence
A command-line tool that scans one or more folders and reports groups of files with exactly the same content, without ever deleting or moving anything.

## The problem it solves
Disks fill up with copies: photos imported twice, a backup of a backup, the same attachment saved in several places. Comparing every file against every other file, or fully hashing every file on a disk, is slow. This tool narrows the candidates in three cheap-to-expensive stages so that most files are never read in full, then tells you which files are identical and how much space the extra copies use.

## Input
- One or more folder paths (required), scanned recursively.
- `--min-size SIZE` — ignore files smaller than this. Accepts plain bytes or a `K`/`M`/`G` suffix (`100`, `10K`, `1.5M`); powers of 1024. Default is 1 byte, so empty files are skipped.
- `--exclude PATTERN` — a glob matched against the path relative to the scanned folder or against the file name (e.g. `"*.tmp"`, `"cache/*"`). Can be repeated.
- `--report FILE` — optional file to also save the results to; must end in `.csv` or `.json`.

## How it works
1. **Validate arguments** (`main` in `dupfind.py`): every folder must exist and be a directory, and `--report` must end in `.csv` or `.json`; otherwise it prints an error and exits with code 2. `parse_size` converts the `--min-size` text into bytes.
2. **Collect files** (`collect_files`): walks each folder with `rglob("*")` in sorted order, skips symlinks and non-regular files, applies the `--exclude` globs (`is_excluded`, using `fnmatch`), and drops files below `--min-size`. Each file is identified by its `(device, inode)` pair, so hard links and folders given twice (e.g. `demo` and `demo/photos`) are counted only once. Files that cannot be `stat`-ed are silently skipped.
3. **Stage 1 – same size** (`find_duplicates` + `regroup`): groups files by size (taken from the file system, no reading). Any file whose size is unique is discarded.
4. **Stage 2 – first 4 KB**: within each same-size group, computes a SHA-256 of only the first 4,096 bytes (`hash_file(path, PREFIX_SIZE)`) and splits the group again. Groups with a single file are discarded.
5. **Stage 3 – full SHA-256**: the remaining candidates are hashed in full with SHA-256, reading in 64 KB chunks (`CHUNK_SIZE`) so memory stays flat for large files. Only files with identical full hashes stay grouped. Files that cannot be read produce a `warning:` line on stderr and are left out.
6. **Statistics**: for each stage it records candidates before and after, and the number of bytes that stage had to read.
7. **Sort and total**: duplicate groups are sorted by wasted space (file size x number of extra copies), largest first. `wasted_space` sums the bytes that could be freed by keeping one copy per group.
8. **Report** (`write_report`): if `--report` was given, writes either a CSV (one row per file: `group,size,sha256,path`) or a JSON list (one object per group with `size`, `sha256`, `paths`).

`make_demo_folder.py DEST` is a helper that creates a reproducible test tree (seeded random bytes, about 18 MB, 26 files) containing exact duplicates, same-size-but-different files, files that share the first 4 KB but differ later, a `cache/` copy and empty files. It refuses to write into a non-empty folder.

## Output
Console output with: number of files and total size scanned, one line per stage (candidates before -> after, how many eliminated, bytes read), the total read versus what hashing everything would have read, then each duplicate group (number of copies, size, first 12 characters of the SHA-256, and the paths), and a final summary line with groups, redundant copies, wasted space and elapsed time.

Exit codes: `0` = no duplicates found, `1` = duplicates found, `2` = bad input.

```text
$ python dupfind.py demo
Scanned 23 files (18.1 MB) in 1 folder(s)

  same size         23 -> 18     candidates (5 eliminated, 0 B read)
  first 4 KB        18 -> 12     candidates (6 eliminated, 72.0 KB read)
  full SHA-256      12 -> 8      candidates (4 eliminated, 8.3 MB read)
  read 8.4 MB in total; hashing every file would read 18.1 MB

Group 1: 4 copies of 830.1 KB  sha256 83c46401d4e6
  demo/backup/beach (copy).jpg
  demo/cache/thumb_src.jpg
  demo/photos/2024/beach.jpg
  demo/photos/to-sort/IMG_0042.jpg
...
3 group(s), 5 redundant copies, 4.8 MB wasted  (0.01s)
```

With `--report dups.csv`, the CSV looks like:

```text
group,size,sha256,path
1,2400000,dac4fe8ffd21549da84d81345c6a2101db79edd0d6de95ee645dace2d9e3710e,demo/backup/old-phone/VID_0001.mp4
1,2400000,dac4fe8ffd21549da84d81345c6a2101db79edd0d6de95ee645dace2d9e3710e,demo/videos/birthday.mp4
```

## Files
- `dupfind.py` — the whole tool: file collection, the three filtering stages, statistics, CSV/JSON report writing and the command-line interface.
- `make_demo_folder.py` — creates the demo folder tree with known duplicates and near-duplicates.
- `tests/test_dupfind.py` — pytest tests using temporary folders (size parsing, hashing, each stage, excludes, hard links, reports).
- `HOW_TO_RUN.txt`, `README.md` — usage instructions and documentation.

## What it does not do
- It never deletes, moves, renames or hard-links files; it only reports.
- It does not detect "similar" files (e.g. resized photos or re-encoded videos); only byte-for-byte identical content counts.
- It does not follow symlinks, and it does not compare files byte-by-byte after hashing; it trusts SHA-256 equality.
- It does not cache hashes between runs or hash files in parallel; each run reads the candidate files again, one at a time.
- Empty files are ignored by default (`--min-size 1`).
