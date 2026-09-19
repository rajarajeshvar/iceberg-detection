from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.schemas import (
    IcebergDetectionRequest,
    TrajectoryPredictionResponse,
    PredictionHorizonItem,
)
from app.services.environmental_service import EnvironmentalService
from app.services.uncertainty_service import UncertaintyService
from app.ml.model import IcebergTrajectoryModel
from app.ml.predict import predict_iceberg_trajectory
from app.database import crud
from app.utils.time import format_iso, parse_timestamp


class TrajectoryService:
    """
    Service layer executing the iceberg trajectory prediction lifecycle.
    """

    def __init__(
        self,
        model: IcebergTrajectoryModel,
        env_service: EnvironmentalService
    ):
        self.model = model
        self.env_service = env_service

    def process_detection_and_predict(
        self,
        db: Session,
        request: IcebergDetectionRequest
    ) -> TrajectoryPredictionResponse:
        """
        Process incoming detection from Feature 1, run trajectory prediction model, and persist records.
        """
        # 1. Save detection record to database
        crud.save_iceberg_detection(db, request)

        # 2. Get environmental conditions (ocean currents, wind, temp, sea ice)
        dt = parse_timestamp(request.timestamp)
        env = self.env_service.get_environmental_conditions(
            latitude=request.latitude,
            longitude=request.longitude,
            timestamp=dt
        )

        # 3. Log environmental data
        crud.save_environmental_data(db, request.latitude, request.longitude, dt, env)

        # 4. Run trajectory model inference across horizons
        horizons = [6, 12, 24, 48, 72]
        pred_coords = predict_iceberg_trajectory(
            model=self.model,
            latitude=request.latitude,
            longitude=request.longitude,
            current_speed=env.current_speed,
            current_direction=env.current_direction,
            wind_speed=env.wind_speed,
            wind_direction=env.wind_direction,
            temperature=env.temperature,
            sea_ice_concentration=env.sea_ice_concentration,
            size_m=request.size_m or 100.0,
            horizons=horizons
        )

        # 5. Calculate uncertainty and build prediction objects
        prediction_items: List[PredictionHorizonItem] = []
        for p in pred_coords:
            h = p["hours_ahead"]
            conf, radius_km = UncertaintyService.calculate_uncertainty(
                hours_ahead=h,
                detection_confidence=request.confidence or 0.90,
                wind_speed=env.wind_speed,
                sea_ice_concentration=env.sea_ice_concentration
            )

            prediction_items.append(
                PredictionHorizonItem(
                    hours_ahead=h,
                    latitude=p["latitude"],
                    longitude=p["longitude"],
                    confidence=conf,
                    uncertainty_radius_km=radius_km
                )
            )

        # 6. Save prediction results to database
        crud.save_trajectory_predictions(
            db=db,
            iceberg_id=request.iceberg_id,
            predictions=prediction_items,
            model_version=self.model.MODEL_VERSION
        )

        # 7. Construct standardization JSON contract response
        gen_time = format_iso(datetime.now(timezone.utc))

        return TrajectoryPredictionResponse(
            iceberg_id=request.iceberg_id,
            prediction_generated_at=gen_time,
            model_version=self.model.MODEL_VERSION,
            predictions=prediction_items
        )

    def get_latest_iceberg_predictions(
        self,
        db: Session,
        iceberg_id: str
    ) -> Optional[TrajectoryPredictionResponse]:
        """
        Retrieve cached or most recent trajectory predictions for an iceberg.
        """
        db_preds = crud.get_latest_predictions(db, iceberg_id)
        if not db_preds:
            return None

        prediction_items = [
            PredictionHorizonItem(
                hours_ahead=p.hours_ahead,
                latitude=p.predicted_latitude,
                longitude=p.predicted_longitude,
                confidence=p.confidence,
                uncertainty_radius_km=p.uncertainty_radius_km
            )
            for p in db_preds
        ]

        model_ver = db_preds[0].model_version if db_preds else self.model.MODEL_VERSION
        gen_time = format_iso(db_preds[0].created_at) if db_preds else format_iso(datetime.now(timezone.utc))

        return TrajectoryPredictionResponse(
            iceberg_id=iceberg_id,
            prediction_generated_at=gen_time,
            model_version=model_ver,
            predictions=prediction_items
        )
