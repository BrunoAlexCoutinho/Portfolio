"""Text maps: '#' wall, '.' open (cost 1), '1'-'9' cell cost, 'S' start, 'G' goal."""

from dataclasses import dataclass
from pathlib import Path

WALL = "#"


@dataclass
class Grid:
    rows: list
    start: tuple
    goal: tuple

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    def cost(self, cell: tuple) -> int:
        """Cost of entering a cell."""
        ch = self.rows[cell[0]][cell[1]]
        return int(ch) if ch.isdigit() else 1

    def neighbors(self, cell: tuple):
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < self.height and 0 <= nc < self.width and self.rows[nr][nc] != WALL:
                yield nr, nc


def parse_map(text: str) -> Grid:
    lines = [line.rstrip("\r\n") for line in text.splitlines()]
    lines = [line for line in lines if line.strip()]
    if not lines:
        raise ValueError("empty map")
    width = max(len(line) for line in lines)
    rows = [line.ljust(width, WALL) for line in lines]   # ragged lines: pad with walls

    start = goal = None
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "S":
                if start:
                    raise ValueError("more than one 'S'")
                start = (r, c)
            elif ch == "G":
                if goal:
                    raise ValueError("more than one 'G'")
                goal = (r, c)
            elif ch not in ".#123456789":
                raise ValueError(f"unknown character {ch!r} at line {r + 1}, column {c + 1}")
    if start is None or goal is None:
        raise ValueError("map needs one 'S' and one 'G'")
    return Grid(rows, start, goal)


def load_map(path) -> Grid:
    return parse_map(Path(path).read_text(encoding="utf-8"))


def draw_path(grid: Grid, path: list) -> str:
    """The map with the path drawn as '*' (start and goal keep their letters)."""
    canvas = [list(row) for row in grid.rows]
    for r, c in path[1:-1]:
        canvas[r][c] = "*"
    return "\n".join("".join(row) for row in canvas)
