import math
from typing import Tuple
from app.models.schemas import EnvironmentalCondition


class UncertaintyService:
    """
    Computes confidence decay and expanding error uncertainty radii for trajectory predictions.
    Uncertainty radius increases non-linearly with forecast horizon and environmental volatility.
    """

    @staticmethod
    def calculate_uncertainty(
        hours_ahead: int,
        detection_confidence: float = 0.90,
        env: float = 1.0,
        wind_speed: float = 12.0,
        sea_ice_concentration: float = 0.5
    ) -> Tuple[float, float]:
        """
        Returns (confidence, uncertainty_radius_km) for a given prediction horizon.
        """
        # Base confidence decay curve: C(t) = C_0 * exp(-lambda * t)
        # e.g., 6h -> ~0.94, 24h -> ~0.82, 72h -> ~0.58
        decay_rate = 0.0065
        base_confidence = detection_confidence * math.exp(-decay_rate * hours_ahead)
        confidence = round(max(0.30, min(0.99, base_confidence)), 2)

        # Base uncertainty growth: R(t) = alpha * t^1.15
        # 6h  -> ~2.1 km
        # 12h -> ~3.8 km
        # 24h -> ~7.4 km
        # 48h -> ~14.2 km
        # 72h -> ~22.5 km
        alpha = 0.28
        base_radius = alpha * (hours_ahead ** 1.15)

        # Environmental volatility scaling factor:
        # Higher wind speed increases position variance
        wind_multiplier = 1.0 + max(0.0, (wind_speed - 10.0) * 0.02)

        # Heavy sea ice dampens drift speed dispersion
        ice_multiplier = 1.0 - 0.2 * max(0.0, min(1.0, sea_ice_concentration))

        uncertainty_radius_km = base_radius * wind_multiplier * ice_multiplier
        uncertainty_radius_km = round(max(0.5, uncertainty_radius_km), 1)

        return confidence, uncertainty_radius_km
