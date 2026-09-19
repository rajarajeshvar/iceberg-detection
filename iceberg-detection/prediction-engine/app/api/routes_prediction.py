from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database import crud
from app.models.schemas import (
    IcebergDetectionRequest,
    TrajectoryPredictionResponse,
    SeaIceForecastRequest,
    SeaIceForecastResponse,
    IcebergListResponse,
    IcebergSummary
)
from app.services.trajectory_service import TrajectoryService
from app.services.prediction_service import PredictionService

router = APIRouter(prefix="/api/v1/prediction", tags=["Prediction Engine"])


def get_trajectory_service() -> TrajectoryService:
    from app.main import container
    return container["trajectory_service"]


def get_prediction_service() -> PredictionService:
    from app.main import container
    return container["prediction_service"]


@router.post(
    "/trajectory",
    response_model=TrajectoryPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Predict iceberg trajectory",
    description="Receive iceberg detection parameters from Feature 1 and return predicted positions for +6h, +12h, +24h, +48h, +72h horizons."
)
def predict_trajectory(
    request: IcebergDetectionRequest,
    db: Session = Depends(get_db),
    service: TrajectoryService = Depends(get_trajectory_service)
):
    try:
        return service.process_detection_and_predict(db, request)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction error: {str(e)}")


@router.get(
    "/trajectory/{iceberg_id}",
    response_model=TrajectoryPredictionResponse,
    summary="Get iceberg predictions by ID",
    description="Retrieve the latest generated trajectory forecast for a specified iceberg ID."
)
def get_trajectory_by_id(
    iceberg_id: str,
    db: Session = Depends(get_db),
    service: TrajectoryService = Depends(get_trajectory_service)
):
    result = service.get_latest_iceberg_predictions(db, iceberg_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trajectory predictions found for iceberg ID '{iceberg_id}'"
        )
    return result


@router.post(
    "/sea-ice",
    response_model=SeaIceForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Forecast sea-ice concentration",
    description="Forecast sea-ice concentration for +6h to +72h based on position and current concentration."
)
def forecast_sea_ice(
    request: SeaIceForecastRequest,
    service: PredictionService = Depends(get_prediction_service)
):
    try:
        return service.forecast_sea_ice(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sea-ice forecast error: {str(e)}")


@router.get(
    "/icebergs",
    response_model=IcebergListResponse,
    summary="List tracked icebergs",
    description="List all icebergs currently registered in the database with their latest detection details."
)
def list_icebergs(db: Session = Depends(get_db)):
    summaries = crud.list_tracked_icebergs(db)
    items = [IcebergSummary(**s) for s in summaries]
    return IcebergListResponse(
        total_icebergs=len(items),
        icebergs=items
    )
