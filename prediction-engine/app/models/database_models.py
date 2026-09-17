from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class IcebergDetectionDB(Base):
    __tablename__ = "iceberg_detections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    iceberg_id = Column(String(50), index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    size_m = Column(Float, nullable=True, default=100.0)
    confidence = Column(Float, nullable=True, default=0.90)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_iceberg_ts", "iceberg_id", "timestamp"),
    )


class TrajectoryPredictionDB(Base):
    __tablename__ = "trajectory_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    iceberg_id = Column(String(50), index=True, nullable=False)
    hours_ahead = Column(Integer, nullable=False)
    predicted_latitude = Column(Float, nullable=False)
    predicted_longitude = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    uncertainty_radius_km = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False, default="baseline-v1")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_pred_iceberg_hrs", "iceberg_id", "hours_ahead"),
    )


class EnvironmentalDataDB(Base):
    __tablename__ = "environmental_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    current_speed = Column(Float, nullable=False)
    current_direction = Column(Float, nullable=False)
    wind_speed = Column(Float, nullable=False)
    wind_direction = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    sea_ice_concentration = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
