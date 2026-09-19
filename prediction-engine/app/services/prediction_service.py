import math
from datetime import datetime, timezone
from typing import List
from app.models.schemas import (
    SeaIceForecastRequest,
    SeaIceForecastResponse,
    SeaIceForecastItem
)
from app.services.environmental_service import EnvironmentalService
from app.utils.time import format_iso, parse_timestamp


class PredictionService:
    """
    High-level facade service for sea-ice concentration forecasting.
    Prototype model combining local thermodynamics and baseline advection trends.
    """

    def __init__(self, env_service: EnvironmentalService):
        self.env_service = env_service

    def forecast_sea_ice(self, request: SeaIceForecastRequest) -> SeaIceForecastResponse:
        """
        Generate sea-ice concentration forecasts for +6h, +12h, +24h, +48h, and +72h horizons.
        """
        dt = parse_timestamp(request.timestamp)

        # Get ambient environment context
        env = self.env_service.get_environmental_conditions(
            latitude=request.latitude,
            longitude=request.longitude,
            timestamp=dt
        )

        horizons = [6, 12, 24, 48, 72]
        items: List[SeaIceForecastItem] = []

        curr_c = request.current_concentration

        for h in horizons:
            # Baseline thermodynamic trend:
            # Below -1.8C ocean temp -> slight freezing freeze trend
            # Above 0C temp -> melting rate
            if env.temperature > 0.0:
                trend = -0.0015 * h * (env.temperature + 0.5)
            elif env.temperature < -1.8:
                trend = 0.0008 * h
            else:
                trend = -0.0005 * h

            # Slight diurnal wave variation
            wave = 0.01 * math.sin(h * math.pi / 12.0)

            forecast_conc = round(max(0.0, min(1.0, curr_c + trend + wave)), 2)

            # Confidence decay with horizon
            conf = round(max(0.50, min(0.98, 0.96 * math.exp(-0.005 * h))), 2)

            items.append(
                SeaIceForecastItem(
                    hours_ahead=h,
                    forecast_concentration=forecast_conc,
                    confidence=conf
                )
            )

        gen_time = format_iso(datetime.now(timezone.utc))

        return SeaIceForecastResponse(
            latitude=request.latitude,
            longitude=request.longitude,
            forecast_generated_at=gen_time,
            current_concentration=request.current_concentration,
            forecasts=items
        )
