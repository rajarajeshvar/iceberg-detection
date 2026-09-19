import math
from typing import Tuple

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the Earth in kilometers.
    """
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_KM * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial bearing (forward azimuth) from point 1 to point 2 in degrees (0-360).
    """
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)

    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(
        phi2
    ) * math.cos(dlambda)

    bearing_rad = math.atan2(y, x)
    bearing_deg = (math.degrees(bearing_rad) + 360.0) % 360.0

    return bearing_deg


def destination_point(
    lat: float, lon: float, bearing_deg: float, distance_km: float
) -> Tuple[float, float]:
    """
    Calculate the destination coordinate given a starting point, initial bearing (degrees), and distance (km).
    """
    validate_coordinates(lat, lon)

    phi1 = math.radians(lat)
    lam1 = math.radians(lon)
    theta = math.radians(bearing_deg)
    delta = distance_km / EARTH_RADIUS_KM

    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta)
        + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )

    lam2 = lam1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )

    # Normalize longitude to -180 to +180
    lam2_deg = math.degrees(lam2)
    lam2_deg = (lam2_deg + 540.0) % 360.0 - 180.0

    lat2_deg = math.degrees(phi2)

    return round(lat2_deg, 6), round(lam2_deg, 6)


def vector_components(speed: float, direction_deg: float) -> Tuple[float, float]:
    """
    Decompose speed and direction (degrees clockwise from North) into u (Eastward) and v (Northward) vector components.
    """
    rad = math.radians(direction_deg)
    u = speed * math.sin(rad)
    v = speed * math.cos(rad)
    return u, v


def speed_direction_from_vectors(u: float, v: float) -> Tuple[float, float]:
    """
    Reconstruct speed and direction (degrees clockwise from North) from u and v vector components.
    """
    speed = math.hypot(u, v)
    direction_rad = math.atan2(u, v)
    direction_deg = (math.degrees(direction_rad) + 360.0) % 360.0
    return speed, direction_deg


def validate_coordinates(lat: float, lon: float) -> None:
    """
    Validate that latitude is within [-90, 90] and longitude is within [-180, 180].
    """
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"Invalid latitude {lat}. Must be between -90 and 90 degrees.")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"Invalid longitude {lon}. Must be between -180 and 180 degrees.")
