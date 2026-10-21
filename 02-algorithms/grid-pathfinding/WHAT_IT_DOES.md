# grid-pathfinding — What it does

## In one sentence
A command-line tool that finds a route from a start cell to a goal cell on a text-file grid map using three classic algorithms (BFS, Dijkstra and A*), draws the route, and compares the algorithms on cost, length, work done and time.

## The problem it solves
Many routing problems (robots in a warehouse, characters in a game, routes on a floor plan) reduce to "find the best path through a grid with obstacles and areas that are harder to cross". BFS, Dijkstra and A* are the standard answers, but they optimise different things and do different amounts of work. Running them side by side on the same maps shows concretely when the fewest-steps route is expensive, and how much exploring a good heuristic saves.

## Input
- A map file in plain text, one row per line:
  - `#` wall (cannot be entered)
  - `.` open cell, cost 1 (`1` also means cost 1)
  - `2`-`9` terrain whose cost is the digit
  - `S` start and `G` goal, exactly one of each (cost 1)
  - Short lines are padded with walls on the right; blank lines are ignored.
- `solve MAP [--algo astar|dijkstra|bfs]` — one map, one algorithm (default `astar`).
- `compare MAP_OR_FOLDER [...] [--repeat N] [--show]` — one or more map files or folders (every `.txt` inside), `--repeat` runs per algorithm (default 5, the fastest time is kept), `--show` also draws the A* path.
- `generate_maps.py [OUTPUT_DIR]` — optional output folder (default `examples/maps`).

## How it works
1. **Parse the map** (`grid.py`, `parse_map` / `load_map`): reads the text, pads ragged lines with `#`, finds `S` and `G`, and rejects unknown characters, a missing `S`/`G` or more than one of either, with a line/column message.
2. **Movement rules** (`Grid.neighbors`, `Grid.cost`): from any cell you can move up, down, left or right into a non-wall cell inside the map. A move costs the cost of the cell you enter.
3. **BFS** (`search.py`, `bfs`): explores the map in rings outward from the start using a FIFO queue (`collections.deque`). It ignores terrain costs, so it returns the path with the fewest steps, which may be expensive.
4. **Dijkstra and A*** (`best_first`): one shared loop using a priority queue (`heapq`). Entries are `(f, h, cell)` where `g` is the cost so far, `h` the heuristic and `f = g + h`. Dijkstra uses `h = 0`; A* (`astar`) uses the Manhattan distance to the goal (`|row difference| + |column difference|`), which never overestimates because every move costs at least 1. Ties on `f` are broken by smaller `h` (closer to the goal), then by cell position, so results are deterministic. A better route to a cell pushes a new heap entry; outdated entries are skipped when popped (the `closed` set). Both return the cheapest path.
5. **Result** (`Result` dataclass): path as a list of (row, col) cells, total cost (sum of entered cells' costs), steps (path length minus 1), nodes expanded (cells taken off the frontier and processed, including the goal), and elapsed seconds (`time.perf_counter`). An empty path means the goal is unreachable.
6. **Display** (`pathfind.py`): `solve` prints the map with the path drawn as `*` (`draw_path`, `S` and `G` keep their letters) and a statistics line. `compare` runs all three algorithms on each map `--repeat` times, keeps the fastest run, and prints a table; unreachable results show `-`.
7. **Map generation** (`generate_maps.py`): builds `maze.txt` (41x21 perfect maze by randomized depth-first search, seed 3) and `big.txt` (60x30, random walls with about 22% probability plus random-walk patches of terrain cost 3, 5 and 9; it tries seeds from 1 upward until BFS confirms a route exists).

## Output
Console output only. `solve` prints the drawn map and one line; `compare` prints one table per map (map size and open-cell count in the header).

Exit codes: `0` = a path was found (on every map), `1` = at least one map has no path, `2` = missing file or invalid map.

```text
$ python pathfind.py solve examples/maps/weighted.txt
##############################
#S******33333.........#......#
#......*33333...9999..#......#
...
#......*****************######
#.......55555555555555.......#
##############################

astar: cost 36, 36 steps, 95 nodes expanded, 1.23 ms

$ python pathfind.py compare examples/maps/weighted.txt
examples/maps/weighted.txt  (30x11, 241 open cells)
  algorithm   cost  steps  expanded   time ms
  bfs           74     32       236      0.33
  dijkstra      36     36       213      0.59
  astar         36     36        95      0.31
```

Times depend on the machine; cost, steps and nodes expanded are deterministic.

## Files
- `grid.py` — map format, parsing and validation, cell costs, 4-direction neighbours, drawing the path with `*`.
- `search.py` — BFS, the shared Dijkstra/A* loop, the Manhattan heuristic, the `Result` dataclass and the `ALGORITHMS` table.
- `pathfind.py` — command-line interface with the `solve` and `compare` commands, repeated timing and exit codes.
- `generate_maps.py` — regenerates `maze.txt` and `big.txt` with fixed seeds.
- `examples/maps/` — `open.txt`, `maze.txt`, `weighted.txt`, `no_path.txt`, `big.txt`.
- `tests/test_search.py` — pytest tests (A* cost equals Dijkstra cost, A* expands no more nodes, path validity, random maps, parse errors).
- `HOW_TO_RUN.txt`, `README.md` — usage instructions and documentation.

## What it does not do
- No diagonal moves; only up, down, left and right.
- Costs are whole numbers 1 to 9 attached to cells; there are no costs on edges, one-way passages or changing maps.
- It does not draw the explored cells, only the final path.
- It does not implement faster variants such as weighted A* or Jump Point Search.
- Timings are pure Python on small maps; they reflect per-node overhead more than real-world performance.
