import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_system_status():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["satellite_data"] == "Connected"
    assert data["trajectory_model"] == "Active"
    assert data["route_engine"] == "Active"
    assert data["ai_assistant"] == "Ready"


def test_get_alerts_endpoint():
    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "total_alerts" in data
    assert "active_alerts" in data
    assert isinstance(data["active_alerts"], list)
    assert data["total_alerts"] >= 1


def test_acknowledge_alert():
    # First fetch active alerts
    res = client.get("/api/v1/alerts")
    alerts = res.json()["active_alerts"]
    assert len(alerts) > 0
    target_id = alerts[0]["alert_id"]

    ack_res = client.post(f"/api/v1/alerts/{target_id}/acknowledge")
    assert ack_res.status_code == 200
    ack_data = ack_res.json()
    assert ack_data["status"] == "ACKNOWLEDGED"


def test_recommendation_reason_endpoint():
    response = client.get("/api/v1/recommendation/reason")
    assert response.status_code == 200
    data = response.json()
    assert "route_changed" in data
    assert "previous_route" in data
    assert "new_route" in data
    assert "reasons" in data
    assert len(data["reasons"]) >= 1
    # Ensure NO numerical overall score in response
    assert "overall_score" not in data


def test_assistant_chat_endpoint():
    payload = {"user_message": "Why is Route 2 recommended?"}
    response = client.post("/api/v1/assistant/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ai_response" in data
    assert len(data["ai_response"]) > 20
    assert "data_source_type" in data
    assert "context_used" in data
    # Grounded response check
    assert "Route 2" in data["ai_response"] or "Route 3" in data["ai_response"]


def test_what_if_simulation_endpoint():
    payload = {
        "scenario_type": "iceberg_speed",
        "change_percent": 20.0
    }
    response = client.post("/api/v1/simulation/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario"] == "iceberg_speed"
    assert "route_impacts" in data
    assert len(data["route_impacts"]) >= 2
    assert "summary_message" in data
    assert "recommended_route" in data


def test_websocket_alerts():
    with client.websocket_connect("/ws/alerts") as websocket:
        # Receives initial active alert broadcast on connection
        data = websocket.receive_json()
        assert "alert_id" in data
        assert "severity" in data
