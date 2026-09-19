import heapq
import math
from typing import List, Tuple, Dict, Any, Optional
from app.utils.geo import haversine_distance
from app.routing.grid import NavigationalGrid


def astar_pathfind(
    grid: NavigationalGrid,
    start: Tuple[float, float],
    destination: Tuple[float, float],
    iceberg_hazards: List[Dict[str, Any]],
    safety_weight: float = 0.5,
    fuel_weight: float = 0.5,
    sea_ice_concentration: float = 0.5,
    lat_bias: float = 0.0
) -> List[Tuple[float, float]]:
    """
    Custom A* pathfinding algorithm on spherical grid.
    Accepts safety weight, fuel weight, and optional spatial bias for route diversity.
    """
    # Snap start & destination to closest grid cells
    start_cell = (round(start[0], 2), round(start[1], 2))
    dest_cell = (round(destination[0], 2), round(destination[1], 2))

    # Priority queue storing (f_score, counter, current_node)
    counter = 0
    open_set = []
    heapq.heappush(open_set, (0.0, counter, start_cell))

    came_from: Dict[Tuple[float, float], Tuple[float, float]] = {}
    g_score: Dict[Tuple[float, float], float] = {start_cell: 0.0}

    visited = set()

    max_iterations = 2500
    iterations = 0

    while open_set and iterations < max_iterations:
        iterations += 1
        current_f, _, current = heapq.heappop(open_set)

        if current in visited:
            continue
        visited.add(current)

        # Reached destination proximity (within 1 grid step)
        if haversine_distance(current[0], current[1], dest_cell[0], dest_cell[1]) <= grid.resolution_deg * 111.0:
            # Reconstruct path
            path = [dest_cell]
            curr = current
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.append(start_cell)
            path.reverse()
            return _smooth_path(path)

        for neighbor in grid.get_neighbors(current):
            if neighbor in visited:
                continue

            # Cell cost + spatial bias for route diversity
            cell_cost = grid.calculate_cell_cost(
                from_node=current,
                to_node=neighbor,
                iceberg_hazards=iceberg_hazards,
                safety_weight=safety_weight,
                fuel_weight=fuel_weight,
                sea_ice_concentration=sea_ice_concentration
            )

            # Apply spatial offset bias if requested (e.g. north vs south detour preference)
            if lat_bias != 0.0:
                # Add penalty if moving away from preferred latitude bias direction
                cell_cost += max(0.0, (neighbor[0] - current[0]) * lat_bias * 25.0)

            tentative_g = g_score[current] + cell_cost

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h_score = haversine_distance(neighbor[0], neighbor[1], dest_cell[0], dest_cell[1])
                f_score = tentative_g + h_score

                counter += 1
                heapq.heappush(open_set, (f_score, counter, neighbor))

    # Fallback to direct linear waypoint interpolation if pathfinding times out
    return _generate_direct_line_path(start, destination, steps=10)


def _smooth_path(raw_path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Subsample and smooth path waypoints.
    """
    if len(raw_path) <= 4:
        return raw_path

    smoothed = [raw_path[0]]
    step = max(1, len(raw_path) // 8)
    for i in range(step, len(raw_path) - 1, step):
        smoothed.append(raw_path[i])
    smoothed.append(raw_path[-1])
    return smoothed


def _generate_direct_line_path(
    start: Tuple[float, float],
    dest: Tuple[float, float],
    steps: int = 10
) -> List[Tuple[float, float]]:
    """
    Generate linear waypoint trajectory between start and destination.
    """
    points = []
    for i in range(steps + 1):
        t = i / float(steps)
        lat = round(start[0] + t * (dest[0] - start[0]), 5)
        lon = round(start[1] + t * (dest[1] - start[1]), 5)
        points.append((lat, lon))
    return points
