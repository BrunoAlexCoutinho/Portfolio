"""Create a demo folder tree with known duplicates and near-duplicates.

Usage: python make_demo_folder.py DEST

What it contains (content is seeded random bytes, about 18 MB in total):
  - exact duplicates: a photo in 3 places, a video and a report in 2 places each
  - same size, different content: 6 "raw" photo files of exactly 1.5 MB
  - same first 4 KB, different ending: 4 log exports with a shared header
  - a cache/ folder with one more copy of the photo (try --exclude "cache/*")
  - unique files of various sizes, and a few empty files
"""

import random
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    dest = Path(sys.argv[1])
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} exists and is not empty", file=sys.stderr)
        return 2

    rng = random.Random(1234)

    def blob(size):
        return rng.randbytes(size)

    def write(relative, data):
        path = dest / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    photo = blob(850_000)
    video = blob(2_400_000)
    report = blob(120_000)
    for p in ["photos/2024/beach.jpg", "photos/to-sort/IMG_0042.jpg", "backup/beach (copy).jpg",
              "cache/thumb_src.jpg"]:
        write(p, photo)
    for p in ["videos/birthday.mp4", "backup/old-phone/VID_0001.mp4"]:
        write(p, video)
    for p in ["documents/report-final.pdf", "documents/sent/report-final.pdf"]:
        write(p, report)

    for i in range(6):
        write(f"photos/raw/DSC_{i:04d}.raw", blob(1_500_000))

    header = blob(4096)
    for i in range(4):
        write(f"logs/export_{i}.log", header + blob(60_000))

    for name, size in [("documents/notes.txt", 3_000), ("documents/budget.xlsx", 45_000),
                       ("music/track01.mp3", 600_000), ("music/track02.mp3", 640_000),
                       ("backup/settings.json", 900)]:
        write(name, blob(size))
    for name in ["documents/empty.txt", "backup/.keep", "logs/.keep"]:
        write(name, b"")

    files = [p for p in dest.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"Created {len(files)} files ({total / 1024 / 1024:.1f} MB) in {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
