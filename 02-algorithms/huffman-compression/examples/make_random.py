"""Write a file of random bytes, to show that random data does not compress.

Usage: python examples/make_random.py OUTPUT [--size BYTES] [--seed N]
"""

import argparse
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a file of seeded random bytes.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--size", type=int, default=20_000, help="bytes (default 20000)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    data = random.Random(args.seed).randbytes(args.size)
    args.output.write_bytes(data)
    print(f"Wrote {args.size:,} random bytes to {args.output}")


if __name__ == "__main__":
    main()
