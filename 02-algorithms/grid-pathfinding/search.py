"""BFS, Dijkstra and A* on a Grid, with the same result format for comparison."""

import heapq
import time
from collections import deque
from dataclasses import dataclass

from grid import Grid


@dataclass
class Result:
    algorithm: str
    path: list          # list of (row, col) from start to goal, empty if unreachable
    cost: int           # sum of the costs of the cells entered
    expanded: int       # nodes taken off the frontier and expanded
    seconds: float

    @property
    def found(self) -> bool:
        return bool(self.path)

    @property
    def steps(self) -> int:
        return len(self.path) - 1 if self.path else 0


def rebuild(came_from: dict, goal: tuple) -> list:
    path = [goal]
    while came_from[path[-1]] is not None:
        path.append(came_from[path[-1]])
    return path[::-1]


def path_cost(grid: Grid, path: list) -> int:
    return sum(grid.cost(cell) for cell in path[1:])


def bfs(grid: Grid) -> Result:
    """Fewest steps. Ignores cell costs, so the path can be expensive."""
    t0 = time.perf_counter()
    came_from = {grid.start: None}
    queue = deque([grid.start])
    expanded = 0
    while queue:
        cell = queue.popleft()
        expanded += 1
        if cell == grid.goal:
            path = rebuild(came_from, cell)
            return Result("bfs", path, path_cost(grid, path), expanded, time.perf_counter() - t0)
        for nxt in grid.neighbors(cell):
            if nxt not in came_from:
                came_from[nxt] = cell
                queue.append(nxt)
    return Result("bfs", [], 0, expanded, time.perf_counter() - t0)


def best_first(grid: Grid, heuristic, name: str) -> Result:
    """Shared loop of Dijkstra (heuristic = 0) and A*.

    Heap entries are (f, h, cell): among equal f, the node closer to the goal
    goes first, and comparing the cell tuples makes ties deterministic.
    """
    t0 = time.perf_counter()
    g = {grid.start: 0}
    came_from = {grid.start: None}
    heap = [(heuristic(grid.start), heuristic(grid.start), grid.start)]
    closed = set()
    while heap:
        _, _, cell = heapq.heappop(heap)
        if cell in closed:
            continue        # stale entry, a cheaper one was already expanded
        closed.add(cell)
        if cell == grid.goal:
            path = rebuild(came_from, cell)
            return Result(name, path, g[cell], len(closed), time.perf_counter() - t0)
        for nxt in grid.neighbors(cell):
            new_g = g[cell] + grid.cost(nxt)
            if new_g < g.get(nxt, float("inf")):
                g[nxt] = new_g
                came_from[nxt] = cell
                h = heuristic(nxt)
                heapq.heappush(heap, (new_g + h, h, nxt))
    return Result(name, [], 0, len(closed), time.perf_counter() - t0)


def dijkstra(grid: Grid) -> Result:
    return best_first(grid, lambda cell: 0, "dijkstra")


def astar(grid: Grid) -> Result:
    # Manhattan distance never overestimates: every move costs at least 1.
    gr, gc = grid.goal
    return best_first(grid, lambda cell: abs(cell[0] - gr) + abs(cell[1] - gc), "astar")


ALGORITHMS = {"bfs": bfs, "dijkstra": dijkstra, "astar": astar}
