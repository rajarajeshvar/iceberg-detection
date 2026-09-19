from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.database_models import IcebergDetectionDB, TrajectoryPredictionDB, EnvironmentalDataDB
from app.models.schemas import IcebergDetectionRequest, PredictionHorizonItem, EnvironmentalCondition
from app.utils.time import parse_timestamp, format_iso


def save_iceberg_detection(db: Session, request: IcebergDetectionRequest) -> IcebergDetectionDB:
    """
    Save a new iceberg detection record from Feature 1.
    """
    detection = IcebergDetectionDB(
        iceberg_id=request.iceberg_id,
        latitude=request.latitude,
        longitude=request.longitude,
        timestamp=parse_timestamp(request.timestamp),
        size_m=request.size_m,
        confidence=request.confidence,
    )
    db.add(detection)
    db.commit()
    db.refresh(detection)
    return detection


def get_historical_detections(db: Session, iceberg_id: str, limit: int = 10) -> List[IcebergDetectionDB]:
    """
    Fetch historical detection positions for a specific iceberg ordered chronologically.
    """
    return (
        db.query(IcebergDetectionDB)
        .filter(IcebergDetectionDB.iceberg_id == iceberg_id)
        .order_by(IcebergDetectionDB.timestamp.asc())
        .limit(limit)
        .all()
    )


def save_trajectory_predictions(
    db: Session,
    iceberg_id: str,
    predictions: List[PredictionHorizonItem],
    model_version: str
) -> List[TrajectoryPredictionDB]:
    """
    Save a set of generated trajectory predictions (+6h, +12h, etc.).
    """
    db_preds = []
    for item in predictions:
        pred = TrajectoryPredictionDB(
            iceberg_id=iceberg_id,
            hours_ahead=item.hours_ahead,
            predicted_latitude=item.latitude,
            predicted_longitude=item.longitude,
            confidence=item.confidence,
            uncertainty_radius_km=item.uncertainty_radius_km,
            model_version=model_version,
        )
        db.add(pred)
        db_preds.append(pred)
    db.commit()
    return db_preds


def get_latest_predictions(db: Session, iceberg_id: str) -> List[TrajectoryPredictionDB]:
    """
    Fetch the most recent set of predictions for a given iceberg.
    """
    subquery = (
        db.query(func.max(TrajectoryPredictionDB.created_at))
        .filter(TrajectoryPredictionDB.iceberg_id == iceberg_id)
        .scalar_subquery()
    )

    return (
        db.query(TrajectoryPredictionDB)
        .filter(
            TrajectoryPredictionDB.iceberg_id == iceberg_id,
            TrajectoryPredictionDB.created_at == subquery
        )
        .order_by(TrajectoryPredictionDB.hours_ahead.asc())
        .all()
    )


def save_environmental_data(
    db: Session,
    latitude: float,
    longitude: float,
    timestamp: datetime,
    env: EnvironmentalCondition
) -> EnvironmentalDataDB:
    """
    Save environmental condition measurements.
    """
    record = EnvironmentalDataDB(
        latitude=latitude,
        longitude=longitude,
        timestamp=parse_timestamp(timestamp),
        current_speed=env.current_speed,
        current_direction=env.current_direction,
        wind_speed=env.wind_speed,
        wind_direction=env.wind_direction,
        temperature=env.temperature,
        sea_ice_concentration=env.sea_ice_concentration,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_tracked_icebergs(db: Session) -> List[dict]:
    """
    List all tracked icebergs with their latest known position and detection count.
    """
    iceberg_ids = db.query(IcebergDetectionDB.iceberg_id).distinct().all()
    summaries = []

    for (ib_id,) in iceberg_ids:
        latest = (
            db.query(IcebergDetectionDB)
            .filter(IcebergDetectionDB.iceberg_id == ib_id)
            .order_by(IcebergDetectionDB.timestamp.desc())
            .first()
        )
        total_count = (
            db.query(func.count(IcebergDetectionDB.id))
            .filter(IcebergDetectionDB.iceberg_id == ib_id)
            .scalar()
        )

        if latest:
            summaries.append({
                "iceberg_id": ib_id,
                "latest_latitude": latest.latitude,
                "latest_longitude": latest.longitude,
                "latest_timestamp": format_iso(latest.timestamp),
                "size_m": latest.size_m,
                "total_detections": total_count,
            })

    return summaries
