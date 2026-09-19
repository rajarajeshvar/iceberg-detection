import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "mock_data_enabled" in data


def test_post_trajectory_valid():
    payload = {
        "iceberg_id": "IB_TEST_001",
        "latitude": -64.231,
        "longitude": 42.512,
        "timestamp": "2026-09-14T10:00:00Z",
        "size_m": 145.0,
        "confidence": 0.94
    }
    response = client.post("/api/v1/prediction/trajectory", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["iceberg_id"] == "IB_TEST_001"
    assert "predictions" in data
    assert len(data["predictions"]) == 5

    horizons = [p["hours_ahead"] for p in data["predictions"]]
    assert horizons == [6, 12, 24, 48, 72]

    # Verify uncertainty increases with horizon
    rad_6h = data["predictions"][0]["uncertainty_radius_km"]
    rad_72h = data["predictions"][-1]["uncertainty_radius_km"]
    assert rad_72h > rad_6h


def test_get_trajectory_by_id():
    # First create detection
    payload = {
        "iceberg_id": "IB_TEST_002",
        "latitude": -64.500,
        "longitude": 43.100,
        "timestamp": "2026-09-14T12:00:00Z",
        "size_m": 200.0,
        "confidence": 0.91
    }
    client.post("/api/v1/prediction/trajectory", json=payload)

    # Now GET
    response = client.get("/api/v1/prediction/trajectory/IB_TEST_002")
    assert response.status_code == 200
    data = response.json()
    assert data["iceberg_id"] == "IB_TEST_002"
    assert len(data["predictions"]) == 5


def test_post_sea_ice_forecast():
    payload = {
        "latitude": -64.2,
        "longitude": 42.5,
        "timestamp": "2026-09-14T10:00:00Z",
        "current_concentration": 0.72
    }
    response = client.post("/api/v1/prediction/sea-ice", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["latitude"] == -64.2
    assert len(data["forecasts"]) == 5
    assert data["forecasts"][0]["hours_ahead"] == 6


def test_invalid_latitude():
    payload = {
        "iceberg_id": "IB_INVALID",
        "latitude": -95.0,  # Invalid
        "longitude": 42.512,
        "timestamp": "2026-09-14T10:00:00Z"
    }
    response = client.post("/api/v1/prediction/trajectory", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_list_icebergs_endpoint():
    response = client.get("/api/v1/prediction/icebergs")
    assert response.status_code == 200
    data = response.json()
    assert "total_icebergs" in data
    assert "icebergs" in data
