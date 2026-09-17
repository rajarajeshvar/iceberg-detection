import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.risk.cpa_tcpa import calculate_cpa_tcpa
from app.risk.safety_score import calculate_safety_score
from app.routing.fuel_score import calculate_fuel_efficiency_score
from app.routing.grid import NavigationalGrid
from app.routing.astar import astar_pathfind
from app.routing.candidate_routes import compute_route_similarity, generate_diverse_candidate_routes
from app.routing.route_optimizer import RouteOptimizerEngine

client = TestClient(app)


def test_cpa_tcpa_calculation():
    # Vessel heading East (-64.0, 40.0) @ 15 knots, Iceberg drifting North (-64.2, 40.5) @ 1 knot
    cpa_km, tcpa_hours = calculate_cpa_tcpa(
        vessel_lat=-64.0, vessel_lon=40.0, vessel_speed_knots=15.0, vessel_course_deg=90.0,
        iceberg_lat=-64.2, iceberg_lon=40.5, iceberg_speed_knots=1.0, iceberg_drift_deg=0.0
    )
    assert cpa_km >= 0.0
    assert tcpa_hours >= 0.0


def test_safety_score_range_and_penalties():
    # Safe route with 30 km clearance
    high_safety = calculate_safety_score(
        min_clearance_km=30.0, cpa_km=25.0, has_intersection=False,
        intersection_count=0, avg_sea_ice_concentration=0.20, avg_wind_speed_ms=10.0
    )
    # Dangerous route with intersection
    low_safety = calculate_safety_score(
        min_clearance_km=3.0, cpa_km=2.0, has_intersection=True,
        intersection_count=3, avg_sea_ice_concentration=0.85, avg_wind_speed_ms=25.0
    )

    assert 0 <= high_safety <= 100
    assert 0 <= low_safety <= 100
    assert high_safety > low_safety


def test_fuel_efficiency_score():
    # Direct baseline route with no deviation
    high_fuel = calculate_fuel_efficiency_score(
        route_distance_km=850.0, baseline_distance_km=850.0,
        estimated_fuel_liters=45000.0, sea_ice_exposure_pct=5.0
    )
    # Long detour route with high sea-ice exposure
    low_fuel = calculate_fuel_efficiency_score(
        route_distance_km=1100.0, baseline_distance_km=850.0,
        estimated_fuel_liters=68000.0, sea_ice_exposure_pct=45.0
    )

    assert 0 <= high_fuel <= 100
    assert 0 <= low_fuel <= 100
    assert high_fuel > low_fuel


def test_route_diversity_constraint():
    grid = NavigationalGrid(resolution_deg=0.25)
    start = (-64.500, 40.200)
    dest = (-63.500, 45.000)
    hazards = [{"latitude": -64.100, "longitude": 42.500, "uncertainty_radius_km": 7.4}]

    orig, r2, r3 = generate_diverse_candidate_routes(grid, start, dest, hazards, sea_ice_concentration=0.5)

    assert len(orig) >= 2
    assert len(r2) >= 2
    assert len(r3) >= 2

    # Verify Route 2 and Route 3 are distinct
    similarity = compute_route_similarity(r2, r3)
    assert similarity <= 0.88


def test_controlled_route2_safety_gt_route3_safety_and_route3_fuel_gt_route2_fuel():
    optimizer = RouteOptimizerEngine(grid_resolution=0.25)
    hazards = [{"latitude": -64.200, "longitude": 42.500, "uncertainty_radius_km": 8.0}]

    res = optimizer.optimize_vessel_routes(
        vessel_id="VESSEL001",
        start_lat=-64.500, start_lon=40.200,
        dest_lat=-63.500, dest_lon=45.000,
        iceberg_predictions=hazards
    )

    routes = {r["route_id"]: r for r in res["routes"]}

    # Controlled Assertion: Route 2 safety > Route 3 safety
    assert routes["route_2"]["safety_score"] > routes["route_3"]["safety_score"]

    # Controlled Assertion: Route 3 fuel > Route 2 fuel
    assert routes["route_3"]["fuel_efficiency_score"] > routes["route_2"]["fuel_efficiency_score"]


def test_post_route_optimize_api():
    payload = {
        "vessel_id": "VESSEL_TEST_01",
        "start_latitude": -64.500,
        "start_longitude": 40.200,
        "dest_latitude": -63.500,
        "dest_longitude": 45.000,
        "safety_weight": 0.70,
        "fuel_weight": 0.30
    }
    response = client.post("/api/v1/route/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["vessel_id"] == "VESSEL_TEST_01"
    assert len(data["routes"]) == 3

    # Check route IDs
    route_ids = [r["route_id"] for r in data["routes"]]
    assert "original" in route_ids
    assert "route_2" in route_ids
    assert "route_3" in route_ids

    # Check rankings
    assert "safety" in data["ranking"]
    assert "fuel_efficiency" in data["ranking"]

    # Check recommendation
    assert "recommendation" in data
    assert data["recommendation"]["route_id"] in ("route_2", "route_3")


def test_weight_change_updates_recommended_route():
    optimizer = RouteOptimizerEngine(grid_resolution=0.25)
    hazards = [{"latitude": -64.200, "longitude": 42.500, "uncertainty_radius_km": 8.0}]

    # High Safety Preference -> Should recommend Route 2
    res_safety = optimizer.optimize_vessel_routes(
        vessel_id="V1", start_lat=-64.5, start_lon=40.2, dest_lat=-63.5, dest_lon=45.0,
        iceberg_predictions=hazards, safety_weight_pref=0.90, fuel_weight_pref=0.10
    )
    assert res_safety["recommendation"]["route_id"] == "route_2"

    # High Fuel Preference -> Should recommend Route 3
    res_fuel = optimizer.optimize_vessel_routes(
        vessel_id="V1", start_lat=-64.5, start_lon=40.2, dest_lat=-63.5, dest_lon=45.0,
        iceberg_predictions=hazards, safety_weight_pref=0.10, fuel_weight_pref=0.90
    )
    assert res_fuel["recommendation"]["route_id"] == "route_3"


def test_post_route_recalculate_api():
    payload = {
        "vessel_id": "VESSEL_RECALC",
        "start_latitude": -64.500,
        "start_longitude": 40.200,
        "dest_latitude": -63.500,
        "dest_longitude": 45.000,
        "new_iceberg": {
            "id": "IB_NEW_999",
            "latitude": -64.150,
            "longitude": 42.800,
            "size_m": 210.0,
            "confidence": 0.96
        }
    }
    response = client.post("/api/v1/route/recalculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["vessel_id"] == "VESSEL_RECALC"
    assert len(data["routes"]) == 3
