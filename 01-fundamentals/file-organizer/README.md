# file-organizer

A command-line tool that sorts the files of a messy folder into subfolders by type or by date, with a dry-run mode and an `undo` command.

## Purpose

A Downloads folder fills up with PDFs, screenshots, installers and zips. Sorting it by hand is boring, and a script that moves files around is only safe if you can see what it will do first and reverse it afterwards. This tool does both: `--dry-run` prints the plan, and every real run writes a move log that `undo` uses to put everything back.

## Features

- `--by category` (default): images, documents, spreadsheets, audio, video, archives, code, other
- `--by date`: `YYYY/MM` folders from each file's modification time
- `--config` to replace the category map with your own JSON
- `--dry-run` prints every planned move and a summary, without touching the disk
- Name collisions become `name (1).ext`, `name (2).ext`, ...
- Every real run is appended to `organizer-log.json`; `undo` reverts the last run and removes the folders it created
- Skips hidden files and folders and the log itself
- Only the top level by default; `--recursive` also takes files from subfolders
- `make_demo_folder.py` builds a realistic messy folder to try it on

## Technologies

- Python 3.10+ (standard library: `pathlib`, `shutil`, `json`, `argparse`)
- pytest for tests

## Installation

No dependencies. Clone and run.

## Usage

```bash
python organize.py sort DIRECTORY [--by category|date] [--config FILE] [--dry-run] [--recursive]
python organize.py undo DIRECTORY
python make_demo_folder.py DEST
```

A custom category file maps folder names to extensions. Anything not listed goes to `other/`:

```json
{
  "photos": [".jpg", ".jpeg", ".png", ".heic", ".webp"],
  "work": [".pdf", ".docx", ".xlsx", ".pptx", ".csv"]
}
```

## Example

Create a demo folder (30 loose files with dates between 2024 and 2026, plus `documents/report.pdf` and `images/IMG_2041.JPG` that already exist, plus two hidden files):

```text
$ python make_demo_folder.py demo
Created 30 files in demo (+ 2 already in subfolders, 2 hidden)

$ python organize.py sort demo --dry-run
Dry run, nothing is moved:
  CV_draft.docx                      -> documents/CV_draft.docx
  IMG_2041.JPG                       -> images/IMG_2041 (1).JPG
  IMG_2042.JPG                       -> images/IMG_2042.JPG
  README.md                          -> documents/README.md
  analysis.py                        -> code/analysis.py
  ...
  report.pdf                         -> documents/report (1).pdf
  ...
  unknown_file                       -> other/unknown_file
  voice-memo.m4a                     -> audio/voice-memo.m4a

30 file(s) would move (archives: 3, audio: 2, code: 5, documents: 7, images: 5, other: 3, spreadsheets: 3, video: 2)
```

`IMG_2041.JPG` and `report.pdf` collide with files already in the target folders, so they get a `(1)` suffix instead of overwriting anything. Running it for real and then undoing:

```text
$ python organize.py sort demo
  ...
30 file(s) moved (archives: 3, audio: 2, code: 5, documents: 7, images: 5, other: 3, spreadsheets: 3, video: 2)
Log written to demo/organizer-log.json, run 'undo' to revert.

$ python organize.py sort demo
Nothing to move.

$ python organize.py undo demo
Restored 30 file(s) to their original place.
```

By date:

```text
$ python organize.py sort demo --by date
  ...
  thesis-v3-FINAL.pdf                -> 2025/02/thesis-v3-FINAL.pdf
  timesheet.ods                      -> 2024/10/timesheet.ods
  unknown_file                       -> 2025/09/unknown_file
  voice-memo.m4a                     -> 2024/04/voice-memo.m4a

30 file(s) moved (2024/01: 1, 2024/02: 2, 2024/03: 2, ..., 2026/06: 1, 2026/08: 1)
```

After `undo`, the 21 month folders and 3 year folders it created are removed again, and only the original `documents/` and `images/` remain.

## How undo works

Each run is stored in the log as a list of `{"from", "to"}` relative paths plus the folders it created. `undo` takes the last run, moves the files back in reverse order and deletes the created folders if they are empty. It refuses to overwrite: if a file has reappeared at the original location, it leaves the moved copy where it is and prints a warning (exit code 1). Several runs can be undone one after another.

## Project Structure

```text
organize.py              planning, moving, logging, undo and CLI
make_demo_folder.py      creates a messy demo folder with varied extensions and dates
examples/categories.json example of a custom category map for --config
tests/                   pytest tests (temporary folders only)
```

## Running the tests

```bash
pip install pytest
pytest
```

## What I Learned

- Separating the plan (a list of moves) from its execution makes dry-run free: it is the same code with the last step skipped.
- Collision handling has to check both the disk and the moves already planned in the same run, or two files with the same name from different folders end up fighting for one slot.
- A reversible operation needs its log written by the operation itself; reconstructing "what was moved" afterwards is guesswork.
- `Path.suffix` only sees the last extension, so `dataset.tar.gz` is matched by `.gz`, which is fine for sorting but worth knowing.

## Possible Improvements

- Write the log after each move, so a run killed halfway (power loss, Ctrl+C) can still be undone
- Rules on file name patterns, e.g. `invoice_*` to `finance/`
- Detect duplicates while sorting instead of only renaming them
- A watch mode that sorts new files as they arrive
