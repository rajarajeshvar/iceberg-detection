import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_feature1_to_feature3_end_to_end_integration():
    """
    Simulates the complete system integration flow:
    1. Feature 1 (Satellite Detection backend) sends a detection POST request.
    2. Prediction Engine processes environmental parameters, extracts features, runs ML inference.
    3. Engine stores detection & prediction records in SQLite DB.
    4. Engine returns a standardized JSON contract response designed for Feature 3 (Risk & Routing Engine).
    """
    # 1. Feature 1 Detection Payload
    feature1_detection_payload = {
        "iceberg_id": "IB_INTEGRATION_999",
        "latitude": -64.231,
        "longitude": 42.512,
        "timestamp": "2026-09-14T10:00:00Z",
        "size_m": 145.0,
        "confidence": 0.94
    }

    # 2. Call Prediction Endpoint
    response = client.post("/api/v1/prediction/trajectory", json=feature1_detection_payload)

    # 3. Assert status code 201 Created
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()

    # 4. Verify standardized JSON contract expected by Feature 3 Risk Engine
    assert data["iceberg_id"] == "IB_INTEGRATION_999"
    assert "prediction_generated_at" in data
    assert "model_version" in data
    assert "predictions" in data

    predictions = data["predictions"]
    assert len(predictions) == 5

    horizons = [p["hours_ahead"] for p in predictions]
    assert horizons == [6, 12, 24, 48, 72]

    for item in predictions:
        assert "hours_ahead" in item
        assert "latitude" in item
        assert "longitude" in item
        assert "confidence" in item
        assert "uncertainty_radius_km" in item

        # Verify latitude and longitude are valid coordinates
        assert -90.0 <= item["latitude"] <= 90.0
        assert -180.0 <= item["longitude"] <= 180.0
        assert 0.0 <= item["confidence"] <= 1.0
        assert item["uncertainty_radius_km"] > 0.0

    # 5. Verify Feature 3 can retrieve predictions asynchronously via GET endpoint
    get_res = client.get("/api/v1/prediction/trajectory/IB_INTEGRATION_999")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["iceberg_id"] == "IB_INTEGRATION_999"
    assert len(get_data["predictions"]) == 5
