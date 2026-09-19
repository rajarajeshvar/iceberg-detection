import math
from typing import List, Dict, Any


def calculate_safety_score(
    min_clearance_km: float,
    cpa_km: float,
    has_intersection: bool,
    intersection_count: int,
    avg_sea_ice_concentration: float,
    avg_wind_speed_ms: float,
    max_uncertainty_radius_km: float = 10.0,
    detection_confidence: float = 0.90
) -> int:
    """
    Calculate a normalized Safety Score (0 = extremely unsafe, 100 = highest safety).
    """
    base_score = 98.0

    # 1. Clearance Distance Penalty
    # Safe clearance >= 25 km -> 0 penalty; < 5 km -> heavy penalty
    if min_clearance_km < 2.0:
        clearance_penalty = 50.0
    elif min_clearance_km < 5.0:
        clearance_penalty = 38.0
    elif min_clearance_km < 10.0:
        clearance_penalty = 24.0
    elif min_clearance_km < 20.0:
        clearance_penalty = 12.0
    elif min_clearance_km < 30.0:
        clearance_penalty = 4.0
    else:
        clearance_penalty = 0.0

    # 2. CPA Penalty
    if cpa_km < 3.0:
        cpa_penalty = 18.0
    elif cpa_km < 8.0:
        cpa_penalty = 10.0
    elif cpa_km < 15.0:
        cpa_penalty = 4.0
    else:
        cpa_penalty = 0.0

    # 3. Hazard Trajectory Intersection Penalty
    if has_intersection:
        intersection_penalty = 25.0 + min(20.0, intersection_count * 5.0)
    else:
        intersection_penalty = 0.0

    # 4. Sea-Ice Exposure Penalty (>0.70 high risk)
    if avg_sea_ice_concentration > 0.80:
        sea_ice_penalty = 15.0
    elif avg_sea_ice_concentration > 0.50:
        sea_ice_penalty = 8.0
    elif avg_sea_ice_concentration > 0.25:
        sea_ice_penalty = 4.0
    else:
        sea_ice_penalty = 0.0

    # 5. Uncertainty & Weather Penalty
    weather_penalty = max(0.0, (avg_wind_speed_ms - 15.0) * 0.5)
    uncertainty_penalty = max(0.0, (max_uncertainty_radius_km - 15.0) * 0.3)

    raw_score = (
        base_score
        - clearance_penalty
        - cpa_penalty
        - intersection_penalty
        - sea_ice_penalty
        - weather_penalty
        - uncertainty_penalty
    )

    # Scale by detection confidence factor
    final_score = raw_score * (0.85 + 0.15 * max(0.5, detection_confidence))

    return int(round(max(0.0, min(100.0, final_score))))
