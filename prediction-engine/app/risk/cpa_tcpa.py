import math
from typing import Dict, List, Tuple, Optional, Any
from app.utils.geo import haversine_distance, calculate_bearing, destination_point, vector_components


def calculate_cpa_tcpa(
    vessel_lat: float,
    vessel_lon: float,
    vessel_speed_knots: float,
    vessel_course_deg: float,
    iceberg_lat: float,
    iceberg_lon: float,
    iceberg_speed_knots: float,
    iceberg_drift_deg: float,
    max_hours_ahead: float = 72.0
) -> Tuple[float, float]:
    """
    Calculate Closest Point of Approach (CPA in km) and Time to CPA (TCPA in hours)
    between a moving vessel and a drifting iceberg using kinematic relative motion vectors.
    """
    # 1. Convert speeds from knots to km/h (1 knot = 1.852 km/h)
    v_vessel_kmh = vessel_speed_knots * 1.852
    v_ice_kmh = iceberg_speed_knots * 1.852

    # 2. Decompose into U (East) and V (North) velocity components (km/h)
    v_u, v_v = vector_components(v_vessel_kmh, vessel_course_deg)
    i_u, i_v = vector_components(v_ice_kmh, iceberg_drift_deg)

    # 3. Relative velocity vector (vessel relative to iceberg)
    rel_u = v_u - i_u
    rel_v = v_v - i_v
    rel_speed = math.hypot(rel_u, rel_v)

    # 4. Initial relative position vector (in km)
    # Approximate Cartesian offsets for small regional steps
    d_lat_km = (iceberg_lat - vessel_lat) * 111.0
    d_lon_km = (iceberg_lon - vessel_lon) * 111.0 * math.cos(math.radians((vessel_lat + iceberg_lat) / 2.0))

    initial_dist_km = haversine_distance(vessel_lat, vessel_lon, iceberg_lat, iceberg_lon)

    if rel_speed < 1e-4:
        return round(initial_dist_km, 2), 0.0

    # 5. Time to Closest Point of Approach: TCPA = - (r . v_rel) / |v_rel|^2
    # Where r is vector from vessel to iceberg (-d_lon_km, -d_lat_km)
    dot_product = -(d_lon_km * rel_u + d_lat_km * rel_v)
    tcpa_hours = dot_product / (rel_speed ** 2)

    # TCPA must be non-negative and bounded by forecast horizon
    if tcpa_hours < 0:
        tcpa_hours = 0.0
    elif tcpa_hours > max_hours_ahead:
        tcpa_hours = max_hours_ahead

    # 6. Position at TCPA
    v_lat_tcpa, v_lon_tcpa = destination_point(vessel_lat, vessel_lon, vessel_course_deg, v_vessel_kmh * tcpa_hours)
    i_lat_tcpa, i_lon_tcpa = destination_point(iceberg_lat, iceberg_lon, iceberg_drift_deg, v_ice_kmh * tcpa_hours)

    cpa_km = haversine_distance(v_lat_tcpa, v_lon_tcpa, i_lat_tcpa, i_lon_tcpa)

    return round(cpa_km, 2), round(tcpa_hours, 2)


def detect_route_hazard_intersections(
    route_points: List[Tuple[float, float]],
    iceberg_predictions: List[Dict[str, Any]],
    danger_threshold_km: float = 12.0
) -> List[Dict[str, Any]]:
    """
    Detect spatial intersections and close proximity encounters between a vessel route and predicted iceberg positions.
    Returns list of hazard intersection alerts with location, distance, horizon, and uncertainty.
    """
    intersections = []
    if len(route_points) < 2 or not iceberg_predictions:
        return intersections

    for pred in iceberg_predictions:
        i_lat = pred["latitude"]
        i_lon = pred["longitude"]
        h_ahead = pred.get("hours_ahead", 24)
        uncertainty_radius = pred.get("uncertainty_radius_km", 5.0)

        # Total danger buffer = baseline safety distance + uncertainty radius
        total_hazard_radius = danger_threshold_km + uncertainty_radius

        for idx in range(len(route_points) - 1):
            p1 = route_points[idx]
            p2 = route_points[idx + 1]

            # Sample 5 sub-points along line segment
            for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
                sample_lat = p1[0] + t * (p2[0] - p1[0])
                sample_lon = p1[1] + t * (p2[1] - p1[1])

                dist_km = haversine_distance(sample_lat, sample_lon, i_lat, i_lon)

                if dist_km <= total_hazard_radius:
                    intersections.append({
                        "latitude": round(sample_lat, 5),
                        "longitude": round(sample_lon, 5),
                        "distance_km": round(dist_km, 2),
                        "hours_ahead": h_ahead,
                        "uncertainty_radius_km": uncertainty_radius,
                        "hazard_type": "PREDICTED HAZARD INTERSECTION"
                    })
                    break  # One alert per segment per prediction horizon

    return intersections
