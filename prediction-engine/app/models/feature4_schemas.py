from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ==========================================
# ALERT SCHEMAS
# ==========================================

class AlertItem(BaseModel):
    alert_id: str = Field(..., json_schema_extra={"example": "ALT_101"})
    event_type: str = Field(..., json_schema_extra={"example": "NEW ICEBERG"})
    severity: str = Field(..., json_schema_extra={"example": "HIGH"}) # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str = Field(..., json_schema_extra={"example": "🧊 NEW ICEBERG DETECTED"})
    message: str = Field(..., json_schema_extra={"example": "Iceberg IB001 detected 28 km away"})
    object_id: Optional[str] = "IB001"
    latitude: Optional[float] = -64.231
    longitude: Optional[float] = 42.512
    timestamp: str = Field(..., json_schema_extra={"example": "2026-09-14T10:00:00Z"})
    status: str = Field("ACTIVE", json_schema_extra={"example": "ACTIVE"}) # ACTIVE, ACKNOWLEDGED, RESOLVED
    cpa_km: Optional[float] = 4.2
    tcpa_hours: Optional[float] = 3.8


class AlertListResponse(BaseModel):
    total_alerts: int
    active_alerts: List[AlertItem]


# ==========================================
# RECOMMENDATION REASON SCHEMAS
# ==========================================

class RecommendationReasonResponse(BaseModel):
    route_changed: bool = Field(True, json_schema_extra={"example": True})
    previous_route: str = Field("route_3", json_schema_extra={"example": "route_3"})
    new_route: str = Field("route_2", json_schema_extra={"example": "route_2"})
    reasons: List[str] = Field(..., json_schema_extra={"example": [
        "New iceberg detected near Route 3",
        "Predicted trajectory reduces Route 3 safety",
        "Route 2 now provides greater hazard clearance"
    ]})


# ==========================================
# AI ASSISTANT CHAT SCHEMAS
# ==========================================

class AssistantChatRequest(BaseModel):
    user_message: str = Field(..., json_schema_extra={"example": "Why is Route 2 recommended?"})


class AssistantChatResponse(BaseModel):
    user_message: str
    ai_response: str
    data_source_type: str = Field("REAL DATA", json_schema_extra={"example": "REAL DATA"})
    grounding_sources: List[str] = Field(default_factory=lambda: ["Feature 1 SAR Detections", "Feature 2 Trajectory Models", "Feature 3 Multi-Route Optimization"])
    confidence: float = Field(0.95, json_schema_extra={"example": 0.95})
    context_used: Dict[str, Any]


# ==========================================
# WHAT-IF SIMULATION SCHEMAS
# ==========================================

class SimulationRequest(BaseModel):
    scenario_type: str = Field(..., json_schema_extra={"example": "iceberg_speed"}) # iceberg_speed, iceberg_heading, sea_ice, original_route
    iceberg_id: Optional[str] = Field("IB001", json_schema_extra={"example": "IB001"})
    change_percent: Optional[float] = Field(20.0, json_schema_extra={"example": 20.0})
    heading_shift_deg: Optional[float] = Field(15.0, json_schema_extra={"example": 15.0})


class RouteSimImpact(BaseModel):
    route_id: str
    route_name: str
    simulated_risk_level: str
    simulated_safety_score: int
    simulated_fuel_score: int
    min_clearance_km: float


class SimulationResponse(BaseModel):
    scenario: str
    change_percent: Optional[float]
    label: str = Field("SIMULATION / WHAT-IF", json_schema_extra={"example": "SIMULATION / WHAT-IF"})
    route_impacts: List[RouteSimImpact]
    recommendation_change: bool
    recommended_route: str
    summary_message: str


# ==========================================
# SYSTEM STATUS SCHEMA
# ==========================================

class SystemStatusResponse(BaseModel):
    satellite_data: str = "Connected"
    trajectory_model: str = "Active"
    route_engine: str = "Active"
    weather_data: str = "Connected"
    ocean_data: str = "Connected"
    ai_assistant: str = "Ready"
    demo_mode: bool = False
