from typing import List, Tuple, Dict, Any
from app.utils.geo import haversine_distance
from app.routing.grid import NavigationalGrid
from app.routing.astar import astar_pathfind, _generate_direct_line_path


def compute_route_similarity(
    route1_points: List[Tuple[float, float]],
    route2_points: List[Tuple[float, float]]
) -> float:
    """
    Compute average spatial deviation (similarity ratio 0.0 to 1.0) between two route trajectories.
    1.0 = identical routes; 0.0 = completely distinct routes.
    """
    if not route1_points or not route2_points:
        return 0.0

    # Sample midpoints
    num_samples = min(len(route1_points), len(route2_points))
    total_diff_km = 0.0

    for i in range(num_samples):
        idx1 = int(i * len(route1_points) / float(num_samples))
        idx2 = int(i * len(route2_points) / float(num_samples))
        d = haversine_distance(
            route1_points[idx1][0], route1_points[idx1][1],
            route2_points[idx2][0], route2_points[idx2][1]
        )
        total_diff_km += d

    avg_diff_km = total_diff_km / float(num_samples)

    # If average deviation is < 5 km, routes are > 90% identical
    similarity = max(0.0, 1.0 - (avg_diff_km / 50.0))
    return round(similarity, 2)


def generate_diverse_candidate_routes(
    grid: NavigationalGrid,
    start: Tuple[float, float],
    dest: Tuple[float, float],
    iceberg_hazards: List[Dict[str, Any]],
    sea_ice_concentration: float = 0.5
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Generate Original Baseline Route, Route 2 (Safety-oriented), and Route 3 (Fuel-oriented),
    strictly enforcing spatial diversity so Route 2 and Route 3 remain distinct alternatives.
    """
    # 1. Original Baseline Route (Direct un-optimized trajectory)
    original_points = _generate_direct_line_path(start, dest, steps=12)

    # 2. Route 2: Safety-Weighted (70% Safety / 30% Fuel)
    route2_points = astar_pathfind(
        grid=grid,
        start=start,
        destination=dest,
        iceberg_hazards=iceberg_hazards,
        safety_weight=0.70,
        fuel_weight=0.30,
        sea_ice_concentration=sea_ice_concentration,
        lat_bias=1.0  # Northward detour preference
    )

    # 3. Route 3: Fuel-Weighted (45% Safety / 55% Fuel)
    route3_points = astar_pathfind(
        grid=grid,
        start=start,
        destination=dest,
        iceberg_hazards=iceberg_hazards,
        safety_weight=0.45,
        fuel_weight=0.55,
        sea_ice_concentration=sea_ice_concentration,
        lat_bias=-1.0  # Direct/Southward preference
    )

    # 4. Route Diversity Check
    similarity = compute_route_similarity(route2_points, route3_points)

    # If Route 2 and Route 3 are too similar (>0.85 similarity), perturb spatial bias for Route 3
    if similarity > 0.85:
        route3_points = astar_pathfind(
            grid=grid,
            start=start,
            destination=dest,
            iceberg_hazards=iceberg_hazards,
            safety_weight=0.30,
            fuel_weight=0.70,
            sea_ice_concentration=sea_ice_concentration,
            lat_bias=-2.5  # Stronger distinct spatial detour
        )

    return original_points, route2_points, route3_points
