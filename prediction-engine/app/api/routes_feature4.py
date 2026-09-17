import os
from typing import List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.models.feature4_schemas import (
    AlertListResponse,
    AlertItem,
    RecommendationReasonResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    SimulationRequest,
    SimulationResponse,
    SystemStatusResponse
)
from app.services.alert_service import AlertService, WebSocketConnectionManager
from app.decision.decision_engine import NavigationDecisionEngine
from app.decision.explanation import generate_explainable_recommendation_reason
from app.ai.assistant import AINavigationAssistant
from app.ai.context_builder import build_system_context
from app.services.simulation_service import SimulationService

router = APIRouter(tags=["Feature 4 — AI Decision Support & Alerts"])

ws_manager = WebSocketConnectionManager()
alert_service = AlertService(ws_manager=ws_manager)
decision_engine = NavigationDecisionEngine()
ai_assistant = AINavigationAssistant()
sim_service = SimulationService()


# ==========================================
# ALERT ENDPOINTS
# ==========================================

@router.get("/api/v1/alerts", response_model=AlertListResponse, summary="Get active alerts")
def get_active_alerts():
    alerts = alert_service.get_active_alerts()
    return AlertListResponse(
        total_alerts=len(alerts),
        active_alerts=alerts
    )


@router.get("/api/v1/alerts/history", response_model=List[AlertItem], summary="Get alert history")
def get_alert_history():
    return alert_service.get_alert_history()


@router.post("/api/v1/alerts/{alert_id}/acknowledge", response_model=AlertItem, summary="Acknowledge an alert")
def acknowledge_alert(alert_id: str):
    alert = alert_service.acknowledge_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert ID '{alert_id}' not found")
    return alert


# ==========================================
# RECOMMENDATION & EXPLANATION ENDPOINTS
# ==========================================

@router.get("/api/v1/recommendation", summary="Get recommended route decision")
def get_recommendation_decision():
    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")

    # Fetch current routes from optimizer
    from app.api.routes_route import optimizer
    route_data = optimizer.optimize_vessel_routes(
        vessel_id="VESSEL001",
        start_lat=-64.500, start_lon=40.200,
        dest_lat=-63.500, dest_lon=45.000,
        iceberg_predictions=[{"latitude": -64.100, "longitude": 42.600, "uncertainty_radius_km": 7.4}]
    )

    decision = decision_engine.evaluate_navigation_state(
        routes=route_data["routes"],
        recommendation=route_data["recommendation"],
        icebergs=[{"id": "IB001"}]
    )

    return {
        "vessel_id": "VESSEL001",
        "data_source": "DEMO / SYNTHETIC DATA" if use_mock else "REAL DATA",
        "recommendation": route_data["recommendation"],
        "decision_evaluation": decision,
        "routes": route_data["routes"]
    }


@router.get("/api/v1/recommendation/reason", response_model=RecommendationReasonResponse, summary="Why did the route change?")
def get_recommendation_reason():
    from app.api.routes_route import optimizer
    route_data = optimizer.optimize_vessel_routes(
        vessel_id="VESSEL001", start_lat=-64.500, start_lon=40.200, dest_lat=-63.500, dest_lon=45.000,
        iceberg_predictions=[{"latitude": -64.100, "longitude": 42.600, "uncertainty_radius_km": 7.4}]
    )

    explanation = generate_explainable_recommendation_reason(
        current_rec_id="route_2",
        previous_rec_id="route_3",
        routes=route_data["routes"],
        new_iceberg_id="IB001"
    )

    return RecommendationReasonResponse(**explanation)


# ==========================================
# WHAT-IF SIMULATION ENDPOINT
# ==========================================

@router.post("/api/v1/simulation/run", response_model=SimulationResponse, summary="Run What-If simulation scenario")
def run_simulation(request: SimulationRequest):
    try:
        return sim_service.run_simulation(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation execution error: {str(e)}")


# ==========================================
# SYSTEM STATUS ENDPOINT
# ==========================================

@router.get("/api/v1/system/status", response_model=SystemStatusResponse, summary="Get system data source status")
def get_system_status():
    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")
    return SystemStatusResponse(
        satellite_data="Connected",
        trajectory_model="Active",
        route_engine="Active",
        weather_data="Connected (Open-Meteo)" if not use_mock else "Connected (Mock)",
        ocean_data="Connected (Open-Meteo)" if not use_mock else "Connected (Mock)",
        ai_assistant="Ready",
        demo_mode=use_mock
    )


# ==========================================
# AI NAVIGATION ASSISTANT CHAT ENDPOINT
# ==========================================

@router.post("/api/v1/assistant/chat", response_model=AssistantChatResponse, summary="Chat with AI Navigation Assistant")
def assistant_chat(request: AssistantChatRequest):
    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")

    from app.api.routes_route import optimizer
    route_data = optimizer.optimize_vessel_routes(
        vessel_id="VESSEL001", start_lat=-64.500, start_lon=40.200, dest_lat=-63.500, dest_lon=45.000,
        iceberg_predictions=[{"latitude": -64.100, "longitude": 42.600, "uncertainty_radius_km": 7.4}]
    )

    active_alerts = alert_service.get_active_alerts()
    active_alert_dicts = [a.model_dump() for a in active_alerts]

    context = build_system_context(
        vessel_id="VESSEL001",
        vessel_lat=-63.42, vessel_lon=45.21,
        routes=route_data["routes"],
        rankings=route_data["ranking"],
        recommendation=route_data["recommendation"],
        active_alerts=active_alert_dicts,
        is_mock=use_mock
    )

    response_text, context_used = ai_assistant.process_query(request.user_message, context)

    sources = ["Feature 1 SAR Detections", "Feature 2 Trajectory Models", "Feature 3 Multi-Route Optimization"]
    if not use_mock:
        sources.append("Live Open-Meteo Weather/Ocean API")

    return AssistantChatResponse(
        user_message=request.user_message,
        ai_response=response_text,
        data_source_type="DEMO / SYNTHETIC DATA" if use_mock else "REAL DATA",
        grounding_sources=sources,
        confidence=0.96,
        context_used=context_used
    )


# ==========================================
# WEBSOCKET REAL-TIME ALERTS ENDPOINT
# ==========================================

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint broadcasting real-time navigation alerts.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive ping loop
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
