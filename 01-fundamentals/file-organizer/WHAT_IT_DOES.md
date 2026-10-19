# file-organizer — What it does

## In one sentence
A command-line tool that moves the loose files of a folder into subfolders by file type or by modification month, can show the plan before doing anything, and can undo what it did.

## The problem it solves
Folders like Downloads or Desktop collect PDFs, screenshots, installers, spreadsheets and zips in one flat list. Sorting them by hand is tedious, and a script that moves files is only safe if you can preview it and reverse it. This tool prints the planned moves with `--dry-run`, never overwrites existing files, and records every real run in a log so `undo` can put the files back.

## Input
- A command: `sort` or `undo`, followed by the folder to work on.
- For `sort`:
  - `--by category` (default) — group by file extension; or `--by date` — group into `YYYY/MM` folders using each file's modification time.
  - `--config FILE` — optional JSON file that replaces the built-in categories, in the form `{"folder": [".ext", ...]}` (see `examples/categories.json`).
  - `--dry-run` — show the plan only, move nothing.
  - `--recursive` — also take files from subfolders (default is the top level only).
- For `undo`: just the folder. It reads `organizer-log.json` inside that folder.

## How it works
1. **Validate**: `main` in `organize.py` checks that the folder exists (exit code 2 if not). For `sort`, `cmd_sort` loads the category map: the built-in `CATEGORIES`, or the `--config` JSON via `load_categories`, which must be an object whose values are lists. `extension_map` turns it into a lowercase extension -> folder lookup (a missing leading dot is added).
2. **List files** (`list_files`): takes the top-level entries (or everything with `rglob` when `--recursive`), keeps only regular files, skips symlinks, anything whose name or any parent folder starts with `.` (hidden), and the log file `organizer-log.json`. The list is sorted.
3. **Decide the target folder** (`target_folder`): in category mode, the lowercase last extension (`Path.suffix`) is looked up; unknown extensions or files without one go to `other`. Built-in categories are `images`, `documents`, `spreadsheets`, `audio`, `video`, `archives`, `code`. In date mode the folder is `YYYY/MM` from the modification time.
4. **Build the plan** (`make_plan`): a list of (source, destination) pairs. Files already in their correct folder are skipped. `free_name` avoids collisions by checking both the disk and destinations already planned in the same run; a clash becomes `name (1).ext`, `name (2).ext`, and so on. Nothing is touched yet.
5. **Dry run**: if `--dry-run`, `print_plan` prints each move and a count per target folder, then stops.
6. **Apply** (`apply_plan`): creates any missing folders (remembering which ones it created), moves each file with `shutil.move`, and prints a warning (but continues) if a move fails. It then appends one run record (`time`, list of `from`/`to` relative paths, `created_dirs`) to `organizer-log.json`. The log is written once, at the end of the run.
7. **Undo** (`undo_last`): takes the last run from the log, moves files back in reverse order, and refuses to overwrite: if the moved file is missing, or a file has reappeared at the original location, it records a warning and leaves it. It then removes the folders that run created, deepest first, only if they are empty. The run is removed from the log; the log file is deleted when no runs remain. Repeating `undo` reverts earlier runs one by one.

`make_demo_folder.py DEST` creates a demo folder with 30 small placeholder files of varied extensions and modification dates spread over 2024-2026 (fixed random seed), two files already placed in `documents/` and `images/` to provoke name collisions, and two hidden files.

## Output
Console output listing each move as `source -> destination`, followed by a summary with the number of files and a count per folder. A real run also writes `organizer-log.json` in the target folder. `undo` prints how many files were restored, plus warnings on stderr.

Exit codes: `0` = ok; `1` = `undo` could not restore some files; `2` = bad input (not a directory, bad config, nothing to undo).

```text
$ python organize.py sort demo --dry-run
Dry run, nothing is moved:
  CV_draft.docx                      -> documents/CV_draft.docx
  IMG_2041.JPG                       -> images/IMG_2041 (1).JPG
  ...
  report.pdf                         -> documents/report (1).pdf
  unknown_file                       -> other/unknown_file

30 file(s) would move (archives: 3, audio: 2, code: 5, documents: 7, images: 5, other: 3, spreadsheets: 3, video: 2)

$ python organize.py sort demo
  ...
Log written to demo/organizer-log.json, run 'undo' to revert.

$ python organize.py undo demo
Restored 30 file(s) to their original place.
```

## Files
- `organize.py` — the whole tool: category map, file listing, planning, collision-safe naming, moving, the JSON move log, undo and the command-line interface.
- `make_demo_folder.py` — creates a messy demo folder to try the tool on safely.
- `examples/categories.json` — sample custom category map (`photos`, `work`, `media`, `dev`) for `--config`.
- `tests/test_organize.py` — pytest tests in temporary folders (plans, dry run, collisions, recursive mode, undo, configs).
- `HOW_TO_RUN.txt`, `README.md` — usage instructions and documentation.

## What it does not do
- It does not look inside files; categories are decided only by the last extension (`dataset.tar.gz` is matched by `.gz`) and dates only by modification time.
- It does not handle hidden files or folders (names starting with `.`) or symlinks; they are left in place.
- It does not detect duplicates; a same-name file just gets a `(1)` suffix.
- The log is written only after the whole run, so a run interrupted halfway cannot be undone with `undo`.
- It does not watch the folder or support rules based on file names (e.g. `invoice_*`).
