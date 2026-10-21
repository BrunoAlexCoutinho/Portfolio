"""Generate the maze and the big terrain map in examples/maps/ (fixed seeds).

Usage: python generate_maps.py [OUTPUT_DIR]     (default examples/maps)
"""

import random
import sys
from pathlib import Path

from grid import parse_map
from search import bfs


def make_maze(width: int, height: int, seed: int) -> str:
    """Perfect maze (exactly one route between two cells) by randomized depth-first search."""
    rng = random.Random(seed)
    cells = [["#"] * width for _ in range(height)]
    stack = [(1, 1)]
    cells[1][1] = "."
    while stack:
        r, c = stack[-1]
        options = [(r + dr, c + dc, dr // 2, dc // 2)
                   for dr, dc in ((-2, 0), (2, 0), (0, -2), (0, 2))
                   if 0 < r + dr < height - 1 and 0 < c + dc < width - 1
                   and cells[r + dr][c + dc] == "#"]
        if not options:
            stack.pop()
            continue
        nr, nc, wr, wc = rng.choice(options)
        cells[r + wr][c + wc] = "."
        cells[nr][nc] = "."
        stack.append((nr, nc))
    cells[1][1] = "S"
    cells[height - 2][width - 2] = "G"
    return "\n".join("".join(row) for row in cells) + "\n"


def make_terrain(width: int, height: int, seed: int) -> str:
    """Scattered walls plus patches of sand (3), mud (5) and swamp (9)."""
    rng = random.Random(seed)
    cells = [["." for _ in range(width)] for _ in range(height)]
    for _ in range(14):
        cost = rng.choice("3359")
        r0, c0 = rng.randrange(1, height - 1), rng.randrange(1, width - 1)
        for _ in range(rng.randint(15, 45)):           # random-walk blob
            cells[r0][c0] = cost
            r0 = min(max(r0 + rng.choice((-1, 0, 1)), 1), height - 2)
            c0 = min(max(c0 + rng.choice((-1, 0, 1)), 1), width - 2)
    for r in range(height):
        for c in range(width):
            border = r in (0, height - 1) or c in (0, width - 1)
            if border or rng.random() < 0.22:
                cells[r][c] = "#"
    cells[1][1] = "S"
    cells[height - 2][width - 2] = "G"
    return "\n".join("".join(row) for row in cells) + "\n"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/maps")
    out.mkdir(parents=True, exist_ok=True)

    (out / "maze.txt").write_text(make_maze(41, 21, seed=3), encoding="utf-8")

    seed = 1
    while not bfs(parse_map(text := make_terrain(60, 30, seed))).found:
        seed += 1           # walls are random; keep the first seed with a route
    (out / "big.txt").write_text(text, encoding="utf-8")

    print(f"Wrote {out / 'maze.txt'} (41x21) and {out / 'big.txt'} (60x30, seed {seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
