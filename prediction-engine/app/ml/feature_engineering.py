import math
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from app.utils.geo import vector_components, speed_direction_from_vectors


def compute_coriolis_deflection(wind_u: float, wind_v: float, latitude: float, deflection_angle_deg: float = 30.0) -> Tuple[float, float]:
    """
    In the Southern Hemisphere (latitude < 0), wind leeway turns iceberg movement approx 20-40 degrees left of wind.
    """
    angle_rad = math.radians(-deflection_angle_deg if latitude < 0 else deflection_angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Rotate wind vector
    wind_u_deflected = wind_u * cos_a - wind_v * sin_a
    wind_v_deflected = wind_u * sin_a + wind_v * cos_a

    return wind_u_deflected, wind_v_deflected


def extract_features(
    latitude: float,
    longitude: float,
    current_speed: float,
    current_direction: float,
    wind_speed: float,
    wind_direction: float,
    temperature: float,
    sea_ice_concentration: float,
    size_m: float = 100.0,
    leeway_factor: float = 0.02
) -> Dict[str, float]:
    """
    Extract physics-informed features from current, wind, ice, and geo location.
    """
    # 1. Vector components of current (m/s)
    curr_u, curr_v = vector_components(current_speed, current_direction)

    # 2. Vector components of wind (m/s)
    w_u, w_v = vector_components(wind_speed, wind_direction)

    # 3. Coriolis-deflected wind leeway (Southern Hemisphere deflection)
    w_u_def, w_v_def = compute_coriolis_deflection(w_u, w_v, latitude, deflection_angle_deg=30.0)

    # 4. Sea-ice drag dampening factor (1.0 = open water, 0.3 = heavy ice pack)
    ice_damping = max(0.2, 1.0 - 0.75 * max(0.0, min(1.0, sea_ice_concentration)))

    # 5. Combined kinetic drift velocity vector (m/s)
    # Ocean current is primary driver (~100% current effect) + wind leeway (~2% wind effect)
    net_u_ms = (curr_u + leeway_factor * w_u_def) * ice_damping
    net_v_ms = (curr_v + leeway_factor * w_v_def) * ice_damping

    net_speed_ms, net_direction_deg = speed_direction_from_vectors(net_u_ms, net_v_ms)

    # Convert m/s drift speed to km/hour (1 m/s = 3.6 km/h)
    net_speed_kmh = net_speed_ms * 3.6

    features = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "current_speed": float(current_speed),
        "current_direction": float(current_direction),
        "current_u": float(curr_u),
        "current_v": float(curr_v),
        "wind_speed": float(wind_speed),
        "wind_direction": float(wind_direction),
        "wind_u": float(w_u),
        "wind_v": float(w_v),
        "wind_u_deflected": float(w_u_def),
        "wind_v_deflected": float(w_v_def),
        "temperature": float(temperature),
        "sea_ice_concentration": float(sea_ice_concentration),
        "size_m": float(size_m),
        "ice_damping": float(ice_damping),
        "net_u_ms": float(net_u_ms),
        "net_v_ms": float(net_v_ms),
        "net_speed_kmh": float(net_speed_kmh),
        "net_direction_deg": float(net_direction_deg),
    }

    return features


def feature_dict_to_dataframe(feature_dict: Dict[str, float]) -> pd.DataFrame:
    """
    Convert a feature dictionary into a 1-row Pandas DataFrame matching model expected columns.
    """
    return pd.DataFrame([feature_dict])
