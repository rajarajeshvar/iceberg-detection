import math
from typing import List, Tuple, Dict, Any
from app.utils.geo import haversine_distance


def compute_route_total_distance(points: List[Tuple[float, float]]) -> float:
    """
    Sum Haversine distance across sequential route waypoints in km.
    """
    if len(points) < 2:
        return 0.0
    total_km = 0.0
    for i in range(len(points) - 1):
        total_km += haversine_distance(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
    return round(total_km, 1)


def compute_min_iceberg_clearance(
    points: List[Tuple[float, float]],
    iceberg_predictions: List[Dict[str, Any]]
) -> float:
    """
    Find minimum spatial clearance distance (km) between route waypoints and predicted iceberg positions.
    """
    if not points or not iceberg_predictions:
        return 50.0

    min_dist = 9999.0
    for p in points:
        for pred in iceberg_predictions:
            d = haversine_distance(p[0], p[1], pred["latitude"], pred["longitude"])
            if d < min_dist:
                min_dist = d

    return round(min_dist, 1)


def determine_risk_level(min_clearance_km: float, has_intersection: bool) -> str:
    """
    Determine categorical collision risk level: LOW, MEDIUM, or HIGH.
    """
    if has_intersection or min_clearance_km < 6.0:
        return "HIGH"
    elif min_clearance_km < 15.0:
        return "MEDIUM"
    else:
        return "LOW"


def generate_why_this_route(
    route_id: str,
    safety_score: int,
    fuel_score: int,
    min_clearance_km: float,
    risk_level: str
) -> List[str]:
    """
    Dynamically generate bullet points explaining why this route option was generated.
    """
    if route_id == "original":
        return [
            "Baseline un-optimized trajectory before risk routing",
            "Shortest direct geographical path to destination",
            "Subject to predicted iceberg trajectory intersections"
        ]
    elif route_id == "route_2":
        reasons = [
            f"Avoids predicted iceberg trajectory with {min_clearance_km} km hazard clearance",
            "Maintains high safety margin around predicted drift zones",
            "Adds moderate distance for significant collision risk reduction"
        ]
        if fuel_score >= 88:
            reasons.append("Maintains good fuel efficiency despite detour")
        return reasons
    else:  # route_3
        reasons = [
            "Shorter route deviation with optimized fuel efficiency",
            "Lower estimated fuel consumption than higher-clearance detours",
            f"Maintains acceptable safety clearance ({min_clearance_km} km)",
            "Bypasses major sea-ice resistance areas"
        ]
        return reasons


def compute_comparison_vs_original(
    route_safety: int,
    orig_safety: int,
    route_dist: float,
    orig_dist: float,
    route_fuel: float,
    orig_fuel: float,
    route_risk: str,
    orig_risk: str
) -> Dict[str, str]:
    """
    Generate dynamic comparative metrics against Original Baseline route.
    """
    safety_diff = route_safety - orig_safety

    if orig_dist > 0:
        dist_diff_pct = round(((route_dist - orig_dist) / orig_dist) * 100.0, 1)
    else:
        dist_diff_pct = 0.0

    if orig_fuel > 0:
        fuel_diff_pct = round(((route_fuel - orig_fuel) / orig_fuel) * 100.0, 1)
    else:
        fuel_diff_pct = 0.0

    # Risk reduction estimate
    risk_map = {"HIGH": 80, "MEDIUM": 45, "LOW": 15}
    orig_val = risk_map.get(orig_risk, 80)
    route_val = risk_map.get(route_risk, 15)
    risk_reduction_pct = int(round(((orig_val - route_val) / orig_val) * 100.0))

    return {
        "risk_reduction": f"↓ {max(0, risk_reduction_pct)}% lower",
        "distance_change": f"↑ {max(0.0, dist_diff_pct)}%" if dist_diff_pct >= 0 else f"↓ {abs(dist_diff_pct)}%",
        "fuel_change": f"↑ {max(0.0, fuel_diff_pct)}%" if fuel_diff_pct >= 0 else f"↓ {abs(fuel_diff_pct)}%",
        "safety_increase": f"↑ {max(0, safety_diff)} points"
    }
