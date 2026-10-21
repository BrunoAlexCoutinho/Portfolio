import random
from pathlib import Path

import pytest

from generate_maps import make_maze, make_terrain
from grid import draw_path, load_map, parse_map
from search import astar, bfs, dijkstra, path_cost

MAPS = sorted(Path(__file__).parent.parent.glob("examples/maps/*.txt"))
SOLVABLE = [m for m in MAPS if m.name != "no_path.txt"]


def random_grids(n=40):
    """Small random maps with walls and weights, some without a path."""
    rng = random.Random(0)
    grids = []
    for _ in range(n):
        h, w = rng.randint(3, 12), rng.randint(3, 15)
        rows = [[rng.choice("....#123459") for _ in range(w)] for _ in range(h)]
        rows[0][0], rows[h - 1][w - 1] = "S", "G"
        grids.append(parse_map("\n".join("".join(r) for r in rows)))
    return grids


def check_valid_path(grid, result):
    path = result.path
    assert path[0] == grid.start and path[-1] == grid.goal
    for (r1, c1), (r2, c2) in zip(path, path[1:]):
        assert abs(r1 - r2) + abs(c1 - c2) == 1
        assert grid.rows[r2][c2] != "#"
    assert result.cost == path_cost(grid, path)


def test_example_maps_exist():
    assert {m.name for m in MAPS} >= {"open.txt", "maze.txt", "weighted.txt",
                                      "no_path.txt", "big.txt"}


@pytest.mark.parametrize("map_path", SOLVABLE, ids=lambda p: p.name)
def test_astar_matches_dijkstra_and_expands_less(map_path):
    grid = load_map(map_path)
    a, d = astar(grid), dijkstra(grid)
    check_valid_path(grid, a)
    check_valid_path(grid, d)
    assert a.cost == d.cost
    assert a.expanded <= d.expanded


@pytest.mark.parametrize("map_path", SOLVABLE, ids=lambda p: p.name)
def test_bfs_has_fewest_steps(map_path):
    grid = load_map(map_path)
    b = bfs(grid)
    check_valid_path(grid, b)
    assert b.steps <= dijkstra(grid).steps
    # With every cost set to 1, the cheapest path is the shortest one.
    flat = parse_map("\n".join(r.translate(str.maketrans("123456789", "........."))
                               for r in grid.rows))
    assert b.steps == dijkstra(flat).cost


def test_random_maps_agree():
    for grid in random_grids():
        a, d, b = astar(grid), dijkstra(grid), bfs(grid)
        assert a.found == d.found == b.found
        if d.found:
            assert a.cost == d.cost <= b.cost
            assert a.expanded <= d.expanded


def test_open_field_bfs_is_manhattan_distance():
    grid = parse_map("S....\n.....\n....G")
    assert bfs(grid).steps == 6


def test_weighted_map_bfs_path_is_more_expensive():
    grid = load_map(Path(__file__).parent.parent / "examples/maps/weighted.txt")
    assert bfs(grid).cost > dijkstra(grid).cost


def test_no_path():
    grid = load_map(Path(__file__).parent.parent / "examples/maps/no_path.txt")
    for algorithm in (bfs, dijkstra, astar):
        result = algorithm(grid)
        assert not result.found and result.path == [] and result.steps == 0


def test_goal_next_to_start():
    grid = parse_map("#SG#")
    assert astar(grid).path == [(0, 1), (0, 2)]
    assert astar(grid).cost == 1


def test_parse_errors():
    with pytest.raises(ValueError):
        parse_map("S...\n....")             # no goal
    with pytest.raises(ValueError):
        parse_map("S.G.S")                   # two starts
    with pytest.raises(ValueError):
        parse_map("S.x.G")                   # unknown character


def test_cell_costs_and_ragged_lines():
    grid = parse_map("S9\n.\n.G")
    assert grid.width == 2 and grid.rows[1] == ".#"
    assert grid.cost((0, 1)) == 9 and grid.cost((0, 0)) == 1


def test_draw_path_keeps_start_and_goal():
    grid = parse_map("S...G")
    assert draw_path(grid, astar(grid).path) == "S***G"


def test_generators_produce_solvable_maps():
    assert bfs(parse_map(make_maze(21, 11, seed=1))).found
    grid = parse_map(make_terrain(30, 15, seed=5))
    assert (grid.width, grid.height) == (30, 15)
