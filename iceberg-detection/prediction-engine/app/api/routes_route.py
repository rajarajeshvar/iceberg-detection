from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.models.route_schemas import (
    RouteOptimizationRequest,
    RecalculateRouteRequest,
    RouteOptimizationResponse
)
from app.routing.route_optimizer import RouteOptimizerEngine
from app.services.environmental_service import EnvironmentalService
from app.ml.predict import predict_iceberg_trajectory

router = APIRouter(prefix="/api/v1/route", tags=["Route Optimization & Risk Engine"])

optimizer = RouteOptimizerEngine(grid_resolution=0.20)
env_service = EnvironmentalService(use_mock=True)


def _resolve_predictions(request: RouteOptimizationRequest) -> List[Dict[str, Any]]:
    """
    Resolve iceberg trajectory predictions from request or synthesize using Feature 2 engine.
    """
    hazard_predictions = []

    # 1. If explicit predictions passed in payload (Feature 2 Contract)
    if request.trajectory_predictions:
        for contract in request.trajectory_predictions:
            for item in contract.predictions:
                hazard_predictions.append({
                    "iceberg_id": contract.iceberg_id,
                    "hours_ahead": item.hours_ahead,
                    "latitude": item.latitude,
                    "longitude": item.longitude,
                    "confidence": item.confidence,
                    "uncertainty_radius_km": item.uncertainty_radius_km
                })
        return hazard_predictions

    # 2. If Feature 1 iceberg detections passed, run Feature 2 prediction logic
    if request.icebergs:
        for ib in request.icebergs:
            env = env_service.get_environmental_conditions(ib.latitude, ib.longitude, None)
            from app.main import container
            model = container.get("model")

            preds = predict_iceberg_trajectory(
                model=model,
                latitude=ib.latitude,
                longitude=ib.longitude,
                current_speed=env.current_speed,
                current_direction=env.current_direction,
                wind_speed=env.wind_speed,
                wind_direction=env.wind_direction,
                temperature=env.temperature,
                sea_ice_concentration=env.sea_ice_concentration,
                size_m=ib.size_m or 145.0,
                horizons=[6, 12, 24, 48, 72]
            )

            for p in preds:
                hazard_predictions.append({
                    "iceberg_id": ib.id,
                    "hours_ahead": p["hours_ahead"],
                    "latitude": p["latitude"],
                    "longitude": p["longitude"],
                    "confidence": ib.confidence or 0.94,
                    "uncertainty_radius_km": round(2.0 + 0.35 * p["hours_ahead"], 1)
                })

        return hazard_predictions

    # 3. Default fallback synthetic Antarctic iceberg hazard
    hazard_predictions.append({
        "iceberg_id": "IB001",
        "hours_ahead": 24,
        "latitude": -64.100,
        "longitude": 42.600,
        "confidence": 0.94,
        "uncertainty_radius_km": 7.4
    })
    return hazard_predictions


@router.post(
    "/optimize",
    response_model=RouteOptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimize vessel routes",
    description="Generates Original Route, Route 2, and Route 3 simultaneously with Safety and Fuel Efficient scores, dual rankings, and balanced recommendation."
)
def optimize_routes(request: RouteOptimizationRequest):
    try:
        hazards = _resolve_predictions(request)
        result = optimizer.optimize_vessel_routes(
            vessel_id=request.vessel_id,
            start_lat=request.start_latitude,
            start_lon=request.start_longitude,
            dest_lat=request.dest_latitude,
            dest_lon=request.dest_longitude,
            iceberg_predictions=hazards,
            sea_ice_concentration=0.55,
            safety_weight_pref=request.safety_weight or 0.60,
            fuel_weight_pref=request.fuel_weight or 0.40
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Route optimization error: {str(e)}")


@router.post(
    "/recalculate",
    response_model=RouteOptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Dynamic re-routing",
    description="Recalculate and re-rank all 3 routes dynamically when a new iceberg is detected."
)
def recalculate_routes(request: RecalculateRouteRequest):
    try:
        # Include newly detected iceberg
        if request.new_iceberg:
            if not request.icebergs:
                request.icebergs = []
            request.icebergs.append(request.new_iceberg)

        hazards = _resolve_predictions(request)
        result = optimizer.optimize_vessel_routes(
            vessel_id=request.vessel_id,
            start_lat=request.start_latitude,
            start_lon=request.start_longitude,
            dest_lat=request.dest_latitude,
            dest_lon=request.dest_longitude,
            iceberg_predictions=hazards,
            sea_ice_concentration=0.60,
            safety_weight_pref=request.safety_weight or 0.60,
            fuel_weight_pref=request.fuel_weight or 0.40
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Dynamic re-routing error: {str(e)}")
