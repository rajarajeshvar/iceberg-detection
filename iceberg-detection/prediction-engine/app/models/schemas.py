from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ==========================================
# ICEBERG DETECTION SCHEMAS (FEATURE 1 CONTRACT)
# ==========================================

class IcebergDetectionRequest(BaseModel):
    iceberg_id: str = Field(..., json_schema_extra={"example": "IB001"}, description="Unique iceberg identifier")
    latitude: float = Field(..., json_schema_extra={"example": -64.231}, ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., json_schema_extra={"example": 42.512}, ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    timestamp: datetime = Field(..., json_schema_extra={"example": "2026-09-14T10:00:00Z"}, description="Detection timestamp (ISO-8601)")
    size_m: Optional[float] = Field(100.0, ge=0.0, json_schema_extra={"example": 145.0}, description="Estimated iceberg length/diameter in meters")
    confidence: Optional[float] = Field(0.90, ge=0.0, le=1.0, json_schema_extra={"example": 0.94}, description="Detection confidence score from Feature 1")


# ==========================================
# TRAJECTORY PREDICTION SCHEMAS
# ==========================================

class PredictionHorizonItem(BaseModel):
    hours_ahead: int = Field(..., json_schema_extra={"example": 24}, description="Forecast horizon in hours (6, 12, 24, 48, 72)")
    latitude: float = Field(..., json_schema_extra={"example": -64.11}, description="Predicted latitude")
    longitude: float = Field(..., json_schema_extra={"example": 42.98}, description="Predicted longitude")
    confidence: float = Field(..., json_schema_extra={"example": 0.82}, ge=0.0, le=1.0, description="Prediction confidence score")
    uncertainty_radius_km: float = Field(..., json_schema_extra={"example": 7.4}, ge=0.0, description="Uncertainty radius around predicted position in kilometers")


class TrajectoryPredictionResponse(BaseModel):
    iceberg_id: str = Field(..., json_schema_extra={"example": "IB001"})
    prediction_generated_at: str = Field(..., json_schema_extra={"example": "2026-09-14T10:00:00Z"})
    model_version: str = Field(..., json_schema_extra={"example": "baseline-v1"})
    predictions: List[PredictionHorizonItem]


# ==========================================
# SEA-ICE FORECAST SCHEMAS
# ==========================================

class SeaIceForecastRequest(BaseModel):
    latitude: float = Field(..., json_schema_extra={"example": -64.2}, ge=-90.0, le=90.0)
    longitude: float = Field(..., json_schema_extra={"example": 42.5}, ge=-180.0, le=180.0)
    timestamp: datetime = Field(..., json_schema_extra={"example": "2026-09-14T10:00:00Z"})
    current_concentration: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.72}, description="Current sea-ice concentration ratio (0.0 to 1.0)")


class SeaIceForecastItem(BaseModel):
    hours_ahead: int = Field(..., json_schema_extra={"example": 24})
    forecast_concentration: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.70})
    confidence: float = Field(..., ge=0.0, le=1.0, json_schema_extra={"example": 0.85})


class SeaIceForecastResponse(BaseModel):
    latitude: float
    longitude: float
    forecast_generated_at: str
    current_concentration: float
    forecasts: List[SeaIceForecastItem]


# ==========================================
# ENVIRONMENTAL SCHEMAS
# ==========================================

class EnvironmentalCondition(BaseModel):
    current_speed: float = Field(..., description="Ocean current speed in meters/second")
    current_direction: float = Field(..., description="Ocean current direction in degrees clockwise from North")
    wind_speed: float = Field(..., description="Wind speed in meters/second")
    wind_direction: float = Field(..., description="Wind direction in degrees clockwise from North")
    temperature: float = Field(..., description="Sea surface temperature in degrees Celsius")
    sea_ice_concentration: float = Field(..., ge=0.0, le=1.0, description="Sea ice concentration fraction (0-1)")


# ==========================================
# MANAGEMENT & HEALTH SCHEMAS
# ==========================================

class IcebergSummary(BaseModel):
    iceberg_id: str
    latest_latitude: float
    latest_longitude: float
    latest_timestamp: str
    size_m: Optional[float]
    total_detections: int


class IcebergListResponse(BaseModel):
    total_icebergs: int
    icebergs: List[IcebergSummary]


class HealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str
    environment: str
    mock_data_enabled: bool
    database_connected: bool
    model_loaded: bool
    model_version: str
