# duplicate-file-finder

A command-line tool that finds files with identical content in one or more folders, using a three-stage filter (size, first 4 KB, full SHA-256) so most files are never read completely.

## Purpose

Disks fill up with copies: the same photos imported twice, a backup of a backup, an attachment saved in three places. Comparing every file with every other one is far too slow, and hashing every file in full reads the whole disk. This tool narrows the candidates step by step and only fully hashes files that are still possible duplicates. It prints how many candidates each stage removed, which shows why the staged approach is fast.

## Features

- Scans one or more folders recursively
- Stage 1: group by size (no reads at all)
- Stage 2: SHA-256 of the first 4 KB, only for files that share a size
- Stage 3: full SHA-256 in 64 KB chunks, only for files that still match
- Per-stage statistics: candidates before/after and bytes read
- Duplicate groups sorted by wasted space, with the total redundant copies and bytes
- `--min-size` (`100`, `10K`, `1M`), repeatable `--exclude` globs, `--report` to CSV or JSON
- Skips symlinks and counts hard links / overlapping folders once
- Exit code `1` when duplicates are found, `0` when none
- **Read-only:** it never deletes or moves anything

## Technologies

- Python 3.10+ (standard library: `hashlib`, `pathlib`, `fnmatch`, `csv`, `json`, `argparse`)
- pytest for tests

## Installation

No dependencies. Clone and run.

## Usage

```bash
python dupfind.py FOLDER [FOLDER ...] [--min-size SIZE] [--exclude PATTERN ...] [--report FILE]
python make_demo_folder.py DEST
```

## Example

`make_demo_folder.py` builds a tree with known traps: a photo in 4 places (one in `cache/`), a video and a report in 2 places, six 1.5 MB "raw" photos of exactly the same size but different content, and four logs that share the same first 4 KB but differ at the end.

```text
$ python make_demo_folder.py demo
Created 26 files (18.1 MB) in demo

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

Group 2: 2 copies of 2.3 MB  sha256 dac4fe8ffd21
  demo/backup/old-phone/VID_0001.mp4
  demo/videos/birthday.mp4

Group 3: 2 copies of 117.2 KB  sha256 bdf93c41f0af
  demo/documents/report-final.pdf
  demo/documents/sent/report-final.pdf

3 group(s), 5 redundant copies, 4.8 MB wasted  (0.01s)
```

Reading the stages: the 5 files with a unique size are dropped without being opened. The six raw photos (9 MB) all have the same size, but their first 4 KB differ, so 24 KB of reads is enough to rule them out. The logs survive stage 2 because of the shared header and are only separated by the full hash. The 3 empty files are ignored (default `--min-size 1`), since every empty file is trivially a "duplicate" of every other.

Narrowing the search and saving a report:

```text
$ python dupfind.py demo --min-size 1M --report dups.csv
Scanned 8 files (13.2 MB) in 1 folder(s)

  same size          8 -> 8      candidates (0 eliminated, 0 B read)
  first 4 KB         8 -> 2      candidates (6 eliminated, 32.0 KB read)
  full SHA-256       2 -> 2      candidates (0 eliminated, 4.6 MB read)
...
1 group(s), 1 redundant copies, 2.3 MB wasted  (0.00s)
Report written to dups.csv
```

```text
group,size,sha256,path
1,2400000,dac4fe8ffd21549da84d81345c6a2101db79edd0d6de95ee645dace2d9e3710e,demo/backup/old-phone/VID_0001.mp4
1,2400000,dac4fe8ffd21549da84d81345c6a2101db79edd0d6de95ee645dace2d9e3710e,demo/videos/birthday.mp4
```

## Why it never deletes

Two files with the same content are not always redundant. A config file may be identical in two projects on purpose, a photo may be in an album folder and in a "to print" folder, and some programs break if a file they own disappears. Which copy to keep depends on context the tool doesn't have. So it only reports: the CSV/JSON output can be reviewed, filtered and then acted on deliberately. A delete option would also turn any bug in the grouping into data loss.

## Project Structure

```text
dupfind.py            scanning, the three stages, reports and CLI
make_demo_folder.py   creates a demo tree with duplicates and near-duplicates
tests/                pytest tests (temporary folders only)
```

## Running the tests

```bash
pip install pytest
pytest
```

## What I Learned

- Cheap filters first: file size is free (it comes from `stat`), a 4 KB prefix is almost free, and the expensive full hash only runs on the few files left.
- The prefix stage catches most different files of equal size, because real files usually differ early (headers, metadata). Files with a shared header are the case that needs stage 3.
- Hard links and overlapping input folders look like duplicates unless files are identified by `(st_dev, st_ino)`.
- Reading in fixed-size chunks keeps memory flat even for multi-GB files.

## Possible Improvements

- Hash files in a thread pool; on SSDs the full-hash stage is I/O-parallel
- Cache hashes by `(path, size, mtime)` to make repeated scans of the same disk faster
- An optional "replace with hard links" mode, with a dry run first
- Byte-by-byte comparison as a final check for people who don't trust hashes
