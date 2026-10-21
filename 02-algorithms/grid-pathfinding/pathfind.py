"""Command line: solve a text map with BFS, Dijkstra or A*, or compare all three."""

import argparse
import sys
from pathlib import Path

from grid import draw_path, load_map
from search import ALGORITHMS


def run(grid, name: str, repeat: int):
    """Run an algorithm `repeat` times and keep the fastest time (less timer noise)."""
    results = [ALGORITHMS[name](grid) for _ in range(repeat)]
    return min(results, key=lambda r: r.seconds)


def cmd_solve(args) -> int:
    grid = load_map(args.map)
    result = run(grid, args.algo, 1)
    print(draw_path(grid, result.path))
    print()
    if not result.found:
        print(f"{args.algo}: no path from S to G ({result.expanded} nodes expanded)")
        return 1
    print(f"{args.algo}: cost {result.cost}, {result.steps} steps, "
          f"{result.expanded} nodes expanded, {result.seconds * 1000:.2f} ms")
    return 0


def cmd_compare(args) -> int:
    status = 0
    paths = []
    for item in map(Path, args.maps):
        paths.extend(sorted(item.glob("*.txt")) if item.is_dir() else [item])
    for path in paths:
        grid = load_map(path)
        open_cells = sum(len(row) - row.count("#") for row in grid.rows)
        print(f"{path}  ({grid.width}x{grid.height}, {open_cells} open cells)")
        print(f"  {'algorithm':<10}{'cost':>6}{'steps':>7}{'expanded':>10}{'time ms':>10}")
        for name in ALGORITHMS:
            r = run(grid, name, args.repeat)
            cost = r.cost if r.found else "-"
            steps = r.steps if r.found else "-"
            print(f"  {name:<10}{cost:>6}{steps:>7}{r.expanded:>10}{r.seconds * 1000:>10.2f}")
            if not r.found:
                status = 1
        if args.show:
            print()
            print(draw_path(grid, ALGORITHMS["astar"](grid).path))
        print()
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Shortest paths on text grid maps.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_solve = sub.add_parser("solve", help="find and draw a path with one algorithm")
    p_solve.add_argument("map")
    p_solve.add_argument("--algo", choices=list(ALGORITHMS), default="astar")
    p_solve.set_defaults(func=cmd_solve)

    p_cmp = sub.add_parser("compare", help="run BFS, Dijkstra and A* and print a table")
    p_cmp.add_argument("maps", nargs="+", help="map files, or folders of .txt maps")
    p_cmp.add_argument("--repeat", type=int, default=5,
                       help="runs per algorithm, the fastest time is shown (default 5)")
    p_cmp.add_argument("--show", action="store_true", help="also draw the A* path")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
