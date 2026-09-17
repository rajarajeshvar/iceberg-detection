from typing import Dict, List, Any, Optional
from app.ml.feature_engineering import extract_features
from app.ml.model import IcebergTrajectoryModel


def predict_iceberg_trajectory(
    model: IcebergTrajectoryModel,
    latitude: float,
    longitude: float,
    current_speed: float,
    current_direction: float,
    wind_speed: float,
    wind_direction: float,
    temperature: float,
    sea_ice_concentration: float,
    size_m: float = 100.0,
    horizons: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Extract features and generate predicted trajectory coordinates across target horizons.
    """
    features = extract_features(
        latitude=latitude,
        longitude=longitude,
        current_speed=current_speed,
        current_direction=current_direction,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        temperature=temperature,
        sea_ice_concentration=sea_ice_concentration,
        size_m=size_m
    )

    return model.predict_trajectory(features, horizons=horizons)
