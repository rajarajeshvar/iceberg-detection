import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from app.utils.geo import destination_point, validate_coordinates
from app.ml.feature_engineering import extract_features, feature_dict_to_dataframe


class IcebergTrajectoryModel:
    """
    Modular wrapper for Antarctic Iceberg Trajectory Prediction.
    Supports trained ML models (RandomForest / XGBoost) and physics-based kinematic fallbacks.
    """

    MODEL_VERSION = "xgboost-physics-v1"
    SUPPORTED_HORIZONS = [6, 12, 24, 48, 72]

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("MODEL_PATH", "./models/iceberg_trajectory_model.joblib")
        self.model_artifacts: Optional[Dict[str, Any]] = None
        self.is_loaded = False
        self.load_model()

    def load_model(self) -> bool:
        """
        Attempt to load serialized ML models from joblib file.
        """
        if self.model_path and os.path.exists(self.model_path):
            try:
                self.model_artifacts = joblib.load(self.model_path)
                self.is_loaded = True
                if isinstance(self.model_artifacts, dict) and "version" in self.model_artifacts:
                    self.MODEL_VERSION = self.model_artifacts["version"]
                return True
            except Exception as e:
                print(f"[Warning] Failed to load model from {self.model_path}: {e}")
                self.is_loaded = False
        return False

    def predict_horizon(self, features: Dict[str, float], hours_ahead: int) -> Tuple[float, float]:
        """
        Predict future (latitude, longitude) for a single horizon (e.g. 24 hours ahead).
        """
        lat = features["latitude"]
        lon = features["longitude"]
        validate_coordinates(lat, lon)

        if self.is_loaded and self.model_artifacts and f"horizon_{hours_ahead}" in self.model_artifacts.get("models", {}):
            try:
                df = feature_dict_to_dataframe(features)
                feature_names = self.model_artifacts.get("feature_names", list(features.keys()))
                X = df[feature_names]

                horizon_models = self.model_artifacts["models"][f"horizon_{hours_ahead}"]
                dist_model = horizon_models["dist"]
                bearing_model = horizon_models["bearing"]

                predicted_dist_km = float(dist_model.predict(X)[0])
                predicted_bearing_deg = float(bearing_model.predict(X)[0]) % 360.0

                pred_lat, pred_lon = destination_point(lat, lon, predicted_bearing_deg, predicted_dist_km)
                return pred_lat, pred_lon
            except Exception as e:
                print(f"[Warning] ML model scoring failed for horizon +{hours_ahead}h: {e}. Using physics fallback.")

        # Physics-based kinematic kinematic drift fallback
        net_speed_kmh = features.get("net_speed_kmh", 1.5)
        net_direction_deg = features.get("net_direction_deg", 45.0)

        # Distance = speed (km/h) * time (hours)
        drift_distance_km = net_speed_kmh * float(hours_ahead)

        pred_lat, pred_lon = destination_point(lat, lon, net_direction_deg, drift_distance_km)
        return pred_lat, pred_lon

    def predict_trajectory(
        self,
        features: Dict[str, float],
        horizons: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Predict positions across all specified forecast horizons.
        """
        target_horizons = horizons or self.SUPPORTED_HORIZONS
        results = []

        for h in target_horizons:
            pred_lat, pred_lon = self.predict_horizon(features, h)
            results.append({
                "hours_ahead": h,
                "latitude": pred_lat,
                "longitude": pred_lon
            })

        return results
