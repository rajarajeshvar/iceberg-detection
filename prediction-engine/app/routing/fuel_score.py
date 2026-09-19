import math


def calculate_fuel_efficiency_score(
    route_distance_km: float,
    baseline_distance_km: float,
    estimated_fuel_liters: float,
    sea_ice_exposure_pct: float,
    wind_headwind_component_ms: float = 0.0,
    current_tailwind_component_ms: float = 0.0
) -> int:
    """
    Calculate a normalized Fuel Efficient Score (0 = least fuel efficient, 100 = most fuel efficient).
    Exact label in user-facing UI must be 'Fuel Efficient'.
    """
    base_score = 100.0

    # 1. Route Deviation Penalty (extra distance relative to baseline direct path)
    if baseline_distance_km > 0:
        deviation_pct = max(0.0, (route_distance_km - baseline_distance_km) / baseline_distance_km) * 100.0
    else:
        deviation_pct = 0.0

    deviation_penalty = deviation_pct * 1.3

    # 2. Sea-Ice Resistance Fuel Penalty
    ice_fuel_penalty = (sea_ice_exposure_pct / 100.0) * 18.0

    # 3. Headwind vs Current Resistance
    wind_penalty = max(0.0, wind_headwind_component_ms * 1.2)
    current_bonus = max(0.0, current_tailwind_component_ms * 1.5)

    raw_score = base_score - deviation_penalty - ice_fuel_penalty - wind_penalty + current_bonus

    return int(round(max(0.0, min(100.0, raw_score))))
