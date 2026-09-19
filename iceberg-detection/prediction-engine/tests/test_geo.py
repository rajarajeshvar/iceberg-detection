import pytest
import math
from app.utils.geo import (
    haversine_distance,
    calculate_bearing,
    destination_point,
    vector_components,
    speed_direction_from_vectors,
    validate_coordinates
)


def test_haversine_distance_zero():
    # Distance from point to itself should be 0.0
    dist = haversine_distance(-64.231, 42.512, -64.231, 42.512)
    assert pytest.approx(dist, abs=1e-3) == 0.0


def test_haversine_distance_known_points():
    # Approx distance between -64.0, 40.0 and -65.0, 40.0 (~111 km per latitude degree)
    dist = haversine_distance(-64.0, 40.0, -65.0, 40.0)
    assert 110.0 <= dist <= 112.0


def test_calculate_bearing_due_south():
    # Bearing from -64.0, 40.0 to -65.0, 40.0 should be approx 180 degrees (South)
    bearing = calculate_bearing(-64.0, 40.0, -65.0, 40.0)
    assert pytest.approx(bearing, abs=1.0) == 180.0


def test_destination_point_roundtrip():
    lat1, lon1 = -64.231, 42.512
    bearing = 45.0
    dist_km = 25.0

    lat2, lon2 = destination_point(lat1, lon1, bearing, dist_km)
    calculated_dist = haversine_distance(lat1, lon1, lat2, lon2)

    assert pytest.approx(calculated_dist, abs=0.1) == dist_km


def test_vector_components_reconstruction():
    speed = 10.0
    direction = 30.0

    u, v = vector_components(speed, direction)
    rec_speed, rec_direction = speed_direction_from_vectors(u, v)

    assert pytest.approx(rec_speed, abs=1e-4) == speed
    assert pytest.approx(rec_direction, abs=1e-4) == direction


def test_invalid_coordinates_raise_error():
    with pytest.raises(ValueError):
        validate_coordinates(-95.0, 42.0)

    with pytest.raises(ValueError):
        validate_coordinates(-64.0, 190.0)
