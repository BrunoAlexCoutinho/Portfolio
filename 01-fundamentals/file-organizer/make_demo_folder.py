"""Create a messy "Downloads"-style folder to try the organizer on.

Usage: python make_demo_folder.py DEST
The files are small placeholders; only names, extensions and dates matter.
Modification dates are spread over 2024-2026 with a fixed seed.
"""

import os
import random
import sys
from datetime import datetime
from pathlib import Path

FILES = [
    "IMG_2041.JPG", "IMG_2042.JPG", "screenshot 2025-03-14.png", "logo-final.svg",
    "holiday_map.webp", "invoice_march.pdf", "CV_draft.docx", "meeting notes.txt",
    "thesis-v3-FINAL.pdf", "README.md", "budget 2025.xlsx", "sales_q1.csv",
    "timesheet.ods", "podcast_ep12.mp3", "voice-memo.m4a", "birthday.mp4",
    "screen-recording.mov", "photos_backup.zip", "dataset.tar.gz", "drivers.7z",
    "analysis.py", "index.html", "query.sql", "config.json", "notebook.ipynb",
    "setup.exe", "font.ttf", "unknown_file", "slides.pptx", "report.pdf",
]

# Files that already exist inside subfolders, to show name collisions.
EXISTING = ["documents/report.pdf", "images/IMG_2041.JPG"]
HIDDEN = [".hidden-settings", ".DS_Store"]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    dest = Path(sys.argv[1])
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} exists and is not empty", file=sys.stderr)
        return 2

    rng = random.Random(42)
    start = datetime(2024, 1, 1).timestamp()
    end = datetime(2026, 9, 30).timestamp()

    for name in FILES + EXISTING + HIDDEN:
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# placeholder for {name}\n" * rng.randint(1, 40), encoding="utf-8")
        stamp = rng.uniform(start, end)
        os.utime(path, (stamp, stamp))

    print(f"Created {len(FILES)} files in {dest} "
          f"(+ {len(EXISTING)} already in subfolders, {len(HIDDEN)} hidden)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
