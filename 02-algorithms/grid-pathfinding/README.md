# grid-pathfinding

BFS, Dijkstra and A* on text-file grid maps with walls and weighted terrain, with a command that runs all three and compares path cost, length, nodes expanded and time.

## Purpose

The three classic shortest-path algorithms are easy to describe and easy to confuse. BFS finds the path with the fewest steps, Dijkstra the cheapest one, and A* the cheapest one while exploring less of the map. Running them side by side on the same maps makes the differences concrete: where BFS picks an expensive route, and how much work the heuristic saves.

## Features

- Maps as plain text: `#` wall, `.` open (cost 1), `2`-`9` terrain cost, `S` start, `G` goal
- Moves in 4 directions; a move costs the cost of the cell it enters
- **BFS** (`collections.deque`): ignores costs, fewest steps
- **Dijkstra** (`heapq`): cheapest path
- **A\*** (`heapq`): Manhattan-distance heuristic, ties broken towards the goal
- For each run: path cost, path length in steps, nodes expanded, time
- `solve` draws the path on the map with `*`
- `compare` prints a table for one or more maps (or a whole folder)
- Five example maps, two of them generated with fixed seeds by `generate_maps.py`

## Technologies

- Python 3.10+ (standard library: `heapq`, `collections.deque`, `dataclasses`, `argparse`)
- pytest for tests

## Installation

No dependencies. Clone and run.

## Usage

```bash
python pathfind.py solve MAP [--algo astar|dijkstra|bfs]
python pathfind.py compare MAP_OR_FOLDER [...] [--repeat N] [--show]
python generate_maps.py [OUTPUT_DIR]
```

## Example

`weighted.txt` has a band of sand (`3`) and a swamp (`9`) between start and goal. BFS goes straight through them:

```text
$ python pathfind.py solve examples/maps/weighted.txt --algo bfs
##############################
#S......33333.........#......#
#*......33333...9999..#......#
#*......33333...9999..#......#
#***********************.....#
#.......33333...9999..#*.....#
#.......33333...9999..#*****G#
#.......33333...9999..#......#
#.......................######
#.......55555555555555.......#
##############################

bfs: cost 74, 32 steps, 236 nodes expanded, 2.24 ms
```

A* walks 4 more steps around the sand and the swamp and pays half:

```text
$ python pathfind.py solve examples/maps/weighted.txt
##############################
#S******33333.........#......#
#......*33333...9999..#......#
#......*33333...9999..#......#
#......*33333...9999.........#
#......*33333...9999..#......#
#......*33333...9999..#*****G#
#......*33333...9999..#*.....#
#......*****************######
#.......55555555555555.......#
##############################

astar: cost 36, 36 steps, 95 nodes expanded, 1.23 ms
```

All maps at once (fastest of 5 runs per algorithm):

```text
$ python pathfind.py compare examples/maps
examples/maps/big.txt  (60x30, 1273 open cells)
  algorithm   cost  steps  expanded   time ms
  bfs          126     86      1264      1.57
  dijkstra      98     90      1258      3.06
  astar         98     90       851      2.44

examples/maps/maze.txt  (41x21, 399 open cells)
  algorithm   cost  steps  expanded   time ms
  bfs          248    248       351      0.48
  dijkstra     248    248       351      0.75
  astar        248    248       346      0.79

examples/maps/no_path.txt  (20x8, 87 open cells)
  algorithm   cost  steps  expanded   time ms
  bfs            -      -        78      0.11
  dijkstra       -      -        78      0.19
  astar          -      -        78      0.21

examples/maps/open.txt  (30x11, 235 open cells)
  algorithm   cost  steps  expanded   time ms
  bfs           35     35       235      0.33
  dijkstra      35     35       235      0.62
  astar         35     35        36      0.10

examples/maps/weighted.txt  (30x11, 241 open cells)
  algorithm   cost  steps  expanded   time ms
  bfs           74     32       236      0.33
  dijkstra      36     36       213      0.59
  astar         36     36        95      0.31
```

What the table shows:

- **open.txt:** with no obstacles in the way, A* expands 36 nodes, essentially only the path itself (35 steps + start). BFS and Dijkstra flood all 235 cells.
- **weighted.txt / big.txt:** BFS's path has the fewest steps but costs 74 vs 36 and 126 vs 98. A* and Dijkstra always agree on the cost.
- **maze.txt:** a perfect maze has exactly one route, so all three return the same path, and the heuristic barely helps (346 vs 351 nodes). The corridors keep pointing away from the goal. Here A*'s extra work per node makes it slower than BFS.
- **no_path.txt:** the goal is walled in. All three explore the 78 reachable cells and stop.
- Timings are in pure Python on small maps, so they mostly reflect per-node overhead: the heap makes Dijkstra slower than BFS for the same number of nodes.

## How it works

- Dijkstra and A* share one loop (`best_first`). The heap holds `(f, h, cell)`; Dijkstra uses `h = 0`, so `f = g`.
- Instead of a decrease-key operation, a better route pushes a new entry and the old one is skipped when popped (the `closed` set). This is the usual way to use `heapq`.
- **Why Manhattan is admissible here:** every move goes to a 4-neighbour and costs at least 1, so reaching the goal takes at least `|dr| + |dc|` moves and costs at least that much. The heuristic never overestimates. It is also consistent (changes by at most 1 per move), so a node never needs to be expanded twice. That also means A* only expands nodes Dijkstra would expand too, which the tests check.
- "Nodes expanded" counts cells taken off the frontier and processed, including the goal.

## Project Structure

```text
grid.py            map parsing, cell costs, neighbours, drawing the path
search.py          BFS, Dijkstra, A* and the Result dataclass
pathfind.py        CLI: solve and compare
generate_maps.py   builds maze.txt (randomized DFS) and big.txt (random walls + terrain)
examples/maps/     open.txt, maze.txt, weighted.txt, no_path.txt, big.txt
tests/             pytest tests
```

## Running the tests

```bash
pip install pytest
pytest
```

## What I Learned

- BFS is only "shortest" in number of edges. As soon as edges have different costs, it can return a path twice as expensive.
- A heuristic only pays off when the map lets you move towards the goal. In a maze it costs time and saves almost nothing.
- Breaking ties on `h` matters on open grids. Many cells share the same `f`; with a plain `(f, cell)` heap, A* expanded all 235 cells of `open.txt` instead of 36.
- Fewer expanded nodes does not automatically mean faster in Python; the constant cost per node (heap operations, heuristic calls) is visible.

## Possible Improvements

- 8-directional moves with diagonal cost √2 and the octile heuristic
- Weighted A* (`f = g + w·h`) to trade optimality for speed, with the cost difference measured
- Jump Point Search for uniform-cost grids
- Draw the expanded cells as well as the path, to show the search frontier
