from dataclasses import dataclass
import heapq
from itertools import count
import json
import sys
from pathlib import Path

if __package__:
    from .grid import Grid, Pose
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from grid.grid import Grid, Pose


@dataclass(frozen=True)
class SearchResult:

    path: list[Pose]
    steps: int
    weight: float
    visited: int


def _heuristic(node: Pose, target: Pose, connectivity: int) -> float:
    row_distance = abs(node[0] - target[0])
    column_distance = abs(node[1] - target[1])
    if connectivity == 8:
        return max(row_distance, column_distance)
    return row_distance + column_distance


def greedy_search(grid: Grid, start: Pose, target: Pose) -> SearchResult:
    start, target = tuple(start), tuple(target)
    if not grid.in_bounds(start) or not grid.in_bounds(target):
        raise ValueError("start and target must be nodes in the grid")
    if start == target:
        return SearchResult([start], 0, 0.0, 1)

    frontier = [(0.0, 0, start)]
    order = count(1)
    parents: dict[Pose, Pose | None] = {start: None}
    visited = 0

    while frontier:
        _, _, current = heapq.heappop(frontier)
        visited += 1
        if current == target:
            path = _reconstruct_path(parents, target)
            return SearchResult(path, len(path) - 1, _path_weight(grid, path), visited)

        for info in grid.neighbors_info(current):
            neighbor = tuple(info["node"])
            if neighbor in parents:
                continue
            parents[neighbor] = current
            priority = _heuristic(neighbor, target, grid.connectivity)
            heapq.heappush(frontier, (priority, next(order), neighbor))

    raise ValueError("no path exists between start and target")


def _reconstruct_path(parents: dict[Pose, Pose | None], target: Pose) -> list[Pose]:
    path = []
    current: Pose | None = target
    while current is not None:
        path.append(current)
        current = parents[current]
    return list(reversed(path))


def _path_weight(grid: Grid, path: list[Pose]) -> float:
    return sum(grid.traversal_cost(source, destination)
               for source, destination in zip(path, path[1:]))


search = greedy_search


def _run_default_mission() -> None:
    config_path = Path(__file__).resolve().parents[1] / "config" / "default.json"
    with config_path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)

    grid = Grid.from_config(
        config["size"],
        config["connectivity"],
        config["agents"],
        [(obstacle["node"], obstacle["weight"])
         for obstacle in config["obstacles"]],
        config["mission"],
    )
    start = tuple(config["mission"]["start"])
    target = tuple(config["mission"]["target"])
    result = greedy_search(grid, start, target)
    threshold = config["mission"]["threshold"]
    status = "success" if result.weight < threshold else "failed"
    path = " -> ".join(str(node) for node in result.path)

    print("Algorithme: Greedy")
    print(f"Noeuds explores: {result.visited}")
    print(f"Deplacements du chemin: {result.steps}")
    print("Poids optimal: non garanti par Greedy")
    print(f"Poids reel du trajet: {result.weight:g}")
    print(f"Statut: {status}")
    print(f"Chemin: {path}")


if __name__ == "__main__":
    _run_default_mission()