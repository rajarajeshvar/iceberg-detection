from typing import Dict, Any, List


def build_system_context(
    vessel_id: str = "VESSEL001",
    vessel_lat: float = -63.42,
    vessel_lon: float = 45.21,
    vessel_speed_knots: float = 14.5,
    dest_lat: float = -64.82,
    dest_lon: float = 51.62,
    routes: List[Dict[str, Any]] = None,
    rankings: Dict[str, Any] = None,
    recommendation: Dict[str, Any] = None,
    active_alerts: List[Dict[str, Any]] = None,
    icebergs: List[Dict[str, Any]] = None,
    is_mock: bool = True
) -> Dict[str, Any]:
    """
    Format current system state into structured JSON context for the AI Navigation Assistant.
    """
    return {
        "data_source_mode": "DEMO / SYNTHETIC DATA" if is_mock else "REAL DATA",
        "vessel": {
            "vessel_id": vessel_id,
            "latitude": vessel_lat,
            "longitude": vessel_lon,
            "speed_knots": vessel_speed_knots,
            "destination_latitude": dest_lat,
            "destination_longitude": dest_lon
        },
        "current_alerts": active_alerts or [],
        "icebergs": icebergs or [],
        "routes": routes or [],
        "route_rankings": rankings or {"safety": ["route_2", "route_3", "original"], "fuel_efficiency": ["route_3", "original", "route_2"]},
        "recommendation": recommendation or {"route_id": "route_2", "label": "Recommended Route", "reason": "Route 2 provides the best balance between safety and fuel efficiency."}
    }
