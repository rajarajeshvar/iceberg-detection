import os
import math
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.ensemble import RandomForestRegressor
try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from app.utils.geo import destination_point, haversine_distance, calculate_bearing
from app.ml.feature_engineering import extract_features, feature_dict_to_dataframe


def generate_synthetic_training_data(num_samples: int = 1500, random_seed: int = 42) -> pd.DataFrame:
    """
    Generate realistic synthetic Antarctic trajectory training data.
    Clearly labeled: DEMO / SYNTHETIC DATA GENERATOR.
    """
    np.random.seed(random_seed)

    # Antarctic sector bounds (Weddell / Ross Sea / Enderby Land region)
    lats = np.random.uniform(-75.0, -60.0, num_samples)
    lons = np.random.uniform(30.0, 160.0, num_samples)

    # Ocean currents (0.1 - 1.2 m/s, direction 0 - 360 deg)
    curr_speeds = np.random.uniform(0.1, 1.2, num_samples)
    curr_dirs = np.random.uniform(0.0, 360.0, num_samples)

    # Winds (2.0 - 25.0 m/s, direction 0 - 360 deg)
    wind_speeds = np.random.uniform(2.0, 25.0, num_samples)
    wind_dirs = np.random.uniform(0.0, 360.0, num_samples)

    # Environmental parameters
    temps = np.random.uniform(-3.0, 2.0, num_samples)
    sea_ice = np.random.uniform(0.0, 0.95, num_samples)
    size_m = np.random.uniform(50.0, 500.0, num_samples)

    records = []
    for i in range(num_samples):
        feats = extract_features(
            latitude=lats[i],
            longitude=lons[i],
            current_speed=curr_speeds[i],
            current_direction=curr_dirs[i],
            wind_speed=wind_speeds[i],
            wind_direction=wind_dirs[i],
            temperature=temps[i],
            sea_ice_concentration=sea_ice[i],
            size_m=size_m[i]
        )

        # For each target horizon (+6h, +12h, +24h, +48h, +72h), generate ground truth displacement
        for h in [6, 12, 24, 48, 72]:
            # Physics distance = speed_kmh * hours
            base_dist_km = feats["net_speed_kmh"] * h
            # Add ocean eddy noise (increases with horizon)
            noise_dist = np.random.normal(0, 0.08 * base_dist_km + 0.5)
            true_dist_km = max(0.1, base_dist_km + noise_dist)

            # Bearing with atmospheric deflection noise
            noise_bearing = np.random.normal(0, 5.0 + 0.1 * h)
            true_bearing_deg = (feats["net_direction_deg"] + noise_bearing + 360.0) % 360.0

            true_lat, true_lon = destination_point(lats[i], lons[i], true_bearing_deg, true_dist_km)

            rec = dict(feats)
            rec["hours_ahead"] = h
            rec["target_dist_km"] = true_dist_km
            rec["target_bearing_deg"] = true_bearing_deg
            rec["target_lat"] = true_lat
            rec["target_lon"] = true_lon
            records.append(rec)

    return pd.DataFrame(records)


def train_and_save_model(output_path: str = "./models/iceberg_trajectory_model.joblib") -> str:
    """
    Train trajectory prediction models for each horizon and save artifacts.
    """
    print("Generating synthetic Antarctic drift training data (DEMO / SYNTHETIC DATA)...")
    df = generate_synthetic_training_data(num_samples=1500)

    feature_cols = [
        "latitude", "longitude", "current_speed", "current_direction",
        "current_u", "current_v", "wind_speed", "wind_direction",
        "wind_u", "wind_v", "wind_u_deflected", "wind_v_deflected",
        "temperature", "sea_ice_concentration", "size_m", "ice_damping",
        "net_u_ms", "net_v_ms", "net_speed_kmh", "net_direction_deg"
    ]

    models_dict = {}
    horizons = [6, 12, 24, 48, 72]

    for h in horizons:
        sub_df = df[df["hours_ahead"] == h]
        X = sub_df[feature_cols]
        y_dist = sub_df["target_dist_km"]
        y_bearing = sub_df["target_bearing_deg"]

        if HAS_XGBOOST:
            dist_model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.08, random_state=42)
            bearing_model = XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.08, random_state=42)
        else:
            dist_model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
            bearing_model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)

        dist_model.fit(X, y_dist)
        bearing_model.fit(X, y_bearing)

        dist_pred = dist_model.predict(X)
        mae_dist = np.mean(np.abs(dist_pred - y_dist))
        print(f"Horizon +{h}h -> Distance Model MAE: {mae_dist:.2f} km")

        models_dict[f"horizon_{h}"] = {
            "dist": dist_model,
            "bearing": bearing_model
        }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    artifacts = {
        "version": "xgboost-physics-v1" if HAS_XGBOOST else "rf-physics-v1",
        "feature_names": feature_cols,
        "models": models_dict,
        "horizons": horizons,
        "data_label": "DEMO / SYNTHETIC DATA"
    }

    joblib.dump(artifacts, output_path)
    print(f"Successfully trained and saved model to {output_path}")
    return output_path


if __name__ == "__main__":
    train_and_save_model()
