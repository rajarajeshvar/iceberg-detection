from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ==========================================
# INPUT CONTRACTS
# ==========================================

class IcebergDetectionInput(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "IB001"})
    latitude: float = Field(..., ge=-90.0, le=90.0, json_schema_extra={"example": -64.231})
    longitude: float = Field(..., ge=-180.0, le=180.0, json_schema_extra={"example": 42.512})
    size_m: Optional[float] = Field(145.0, ge=0.0)
    confidence: Optional[float] = Field(0.94, ge=0.0, le=1.0)


class Feature2PredictionItemInput(BaseModel):
    hours_ahead: int
    latitude: float
    longitude: float
    confidence: float
    uncertainty_radius_km: float


class Feature2PredictionContractInput(BaseModel):
    iceberg_id: str
    predictions: List[Feature2PredictionItemInput]


class RouteOptimizationRequest(BaseModel):
    vessel_id: str = Field("VESSEL001", json_schema_extra={"example": "VESSEL001"})
    start_latitude: float = Field(-64.500, ge=-90.0, le=90.0, json_schema_extra={"example": -64.500})
    start_longitude: float = Field(40.200, ge=-180.0, le=180.0, json_schema_extra={"example": 40.200})
    dest_latitude: float = Field(-63.500, ge=-90.0, le=90.0, json_schema_extra={"example": -63.500})
    dest_longitude: float = Field(45.000, ge=-180.0, le=180.0, json_schema_extra={"example": 45.000})
    icebergs: Optional[List[IcebergDetectionInput]] = None
    trajectory_predictions: Optional[List[Feature2PredictionContractInput]] = None
    safety_weight: Optional[float] = Field(0.60, ge=0.0, le=1.0)
    fuel_weight: Optional[float] = Field(0.40, ge=0.0, le=1.0)


class RecalculateRouteRequest(RouteOptimizationRequest):
    new_iceberg: Optional[IcebergDetectionInput] = None


# ==========================================
# OUTPUT CONTRACTS
# ==========================================

class PointCoordinate(BaseModel):
    latitude: float
    longitude: float


class ComparisonVsOriginal(BaseModel):
    risk_reduction: str
    distance_change: str
    fuel_change: str
    safety_increase: str


class RouteItem(BaseModel):
    route_id: str = Field(..., json_schema_extra={"example": "route_2"})
    route_name: str = Field(..., json_schema_extra={"example": "Route 2"})
    route_type: str = Field(..., json_schema_extra={"example": "optimized"})
    safety_score: int = Field(..., ge=0, le=100, json_schema_extra={"example": 90})
    fuel_efficiency_score: int = Field(..., ge=0, le=100, json_schema_extra={"example": 91})
    distance_km: float = Field(..., json_schema_extra={"example": 920.0})
    travel_time_hours: float = Field(..., json_schema_extra={"example": 61.4})
    estimated_fuel: float = Field(..., json_schema_extra={"example": 52400.0})
    min_clearance_km: float = Field(..., json_schema_extra={"example": 18.2})
    risk_level: str = Field(..., json_schema_extra={"example": "LOW"})
    sea_ice_exposure_pct: float = Field(..., json_schema_extra={"example": 12.0})
    intersections: List[Dict[str, Any]] = []
    points: List[PointCoordinate] = []
    why_this_route: List[str] = []
    comparison_vs_original: Optional[ComparisonVsOriginal] = None


class RouteRanking(BaseModel):
    safety: List[str]
    fuel_efficiency: List[str]


class RouteRecommendation(BaseModel):
    route_id: str = Field(..., json_schema_extra={"example": "route_2"})
    label: str = Field(..., json_schema_extra={"example": "Recommended Route"})
    reason: str = Field(..., json_schema_extra={"example": "Best balance between safety and fuel efficiency."})


class RouteOptimizationResponse(BaseModel):
    vessel_id: str
    routes: List[RouteItem]
    ranking: RouteRanking
    recommendation: RouteRecommendation
