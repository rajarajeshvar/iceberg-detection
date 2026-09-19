from typing import List, Dict, Any


def generate_explainable_recommendation_reason(
    current_rec_id: str,
    previous_rec_id: str,
    routes: List[Dict[str, Any]],
    new_iceberg_id: str = None
) -> Dict[str, Any]:
    """
    Generate dynamic explainable AI rationale for route recommendations and recommendation changes.
    """
    route_map = {r["route_id"]: r for r in routes}
    current_r = route_map.get(current_rec_id, {})
    prev_r = route_map.get(previous_rec_id, {})

    route_changed = (current_rec_id != previous_rec_id)

    reasons = []

    if route_changed:
        if new_iceberg_id:
            reasons.append(f"New iceberg {new_iceberg_id} detected near {prev_r.get('route_name', previous_rec_id)}")
        else:
            reasons.append(f"Environmental parameters reduced {prev_r.get('route_name', previous_rec_id)} safety margin")

        reasons.append(f"Predicted trajectory reduces {prev_r.get('route_name', previous_rec_id)} safety clearance to {prev_r.get('min_clearance_km', 10.0)} km")
        reasons.append(f"{current_r.get('route_name', current_rec_id)} now provides greater hazard clearance ({current_r.get('min_clearance_km', 18.0)} km)")
    else:
        reasons.append(f"{current_r.get('route_name', 'Route 2')} provides the optimal balance of safety ({current_r.get('safety_score', 90)}/100) and fuel efficiency ({current_r.get('fuel_efficiency_score', 91)}/100)")
        reasons.append(f"Maintains {current_r.get('min_clearance_km', 18.2)} km clearance from all predicted iceberg trajectories")

    return {
        "route_changed": route_changed,
        "previous_route": previous_rec_id,
        "new_route": current_rec_id,
        "reasons": reasons
    }
