import math
import os
import httpx
from datetime import datetime
from app.models.schemas import EnvironmentalCondition


class EnvironmentalService:
    """
    Environmental data provider interface.
    Connects to live online Open-Meteo Weather & Marine APIs for real-time wind, temperature, and ocean current parameters.
    Includes automatic fallback to synthetic provider if offline or unreachable.
    """

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock

    def get_environmental_conditions(
        self, latitude: float, longitude: float, timestamp: datetime
    ) -> EnvironmentalCondition:
        """
        Fetch environmental parameters from live online APIs or fallback to mock data generator.
        """
        if not self.use_mock:
            try:
                return self._fetch_online_weather(latitude, longitude)
            except Exception as e:
                print(f"[Warning] Failed to fetch live online weather data ({e}). Falling back to synthetic provider.")

        return self._generate_mock_conditions(latitude, longitude, timestamp)

    def _fetch_online_weather(self, latitude: float, longitude: float) -> EnvironmentalCondition:
        """
        Fetch real-time marine and atmospheric weather parameters from Open-Meteo online API.
        Variables fetched:
          - temperature_2m (°C)
          - wind_speed_10m (m/s converted from km/h)
          - wind_direction_10m (deg)
          - wind_gusts_10m (m/s)
          - ocean_current_velocity (m/s)
          - ocean_current_direction (deg)
        """
        # 1. Fetch Atmospheric Weather from Open-Meteo Forecast API
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}&"
            f"current=temperature_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
        )
        
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(weather_url)
            resp.raise_for_status()
            data = resp.json()

        current_weather = data.get("current", {})
        
        # Wind speed & gusts (Open-Meteo returns km/h by default, convert to m/s)
        wind_speed_kmh = current_weather.get("wind_speed_10m", 15.0)
        wind_speed_ms = round(wind_speed_kmh / 3.6, 2)
        
        wind_gusts_kmh = current_weather.get("wind_gusts_10m", wind_speed_kmh * 1.3)
        wind_gusts_ms = round(wind_gusts_kmh / 3.6, 2)

        wind_direction = float(current_weather.get("wind_direction_10m", 60.0))
        temperature = float(current_weather.get("temperature_2m", -1.5))

        # 2. Fetch Ocean Currents from Open-Meteo Marine API
        curr_speed = 0.45
        curr_dir = 55.0

        try:
            marine_url = (
                f"https://marine-api.open-meteo.com/v1/marine?"
                f"latitude={latitude}&longitude={longitude}&"
                f"current=ocean_current_velocity,ocean_current_direction"
            )
            with httpx.Client(timeout=4.0) as client:
                m_resp = client.get(marine_url)
                if m_resp.status_code == 200:
                    m_data = m_resp.json().get("current", {})
                    if m_data.get("ocean_current_velocity") is not None:
                        curr_speed = float(m_data["ocean_current_velocity"])
                    if m_data.get("ocean_current_direction") is not None:
                        curr_dir = float(m_data["ocean_current_direction"])
        except Exception as me:
            print(f"[Info] Marine current API fallback: {me}")

        # Estimate sea ice concentration based on location and surface temperature
        lat_factor = max(0.0, min(1.0, (-latitude - 60.0) / 20.0))
        sea_ice = round(max(0.10, min(0.95, 0.35 + 0.50 * lat_factor - 0.05 * temperature)), 2)

        # Incorporate wind gust factor into overall effective wind speed for prediction engine
        effective_wind_speed = round(max(wind_speed_ms, wind_speed_ms * 0.8 + wind_gusts_ms * 0.2), 2)

        return EnvironmentalCondition(
            current_speed=curr_speed,
            current_direction=curr_dir,
            wind_speed=effective_wind_speed,
            wind_direction=wind_direction,
            temperature=temperature,
            sea_ice_concentration=sea_ice
        )

    def _generate_mock_conditions(
        self, latitude: float, longitude: float, timestamp: datetime
    ) -> EnvironmentalCondition:
        """
        Generate deterministic, location-and-time-seeded synthetic Antarctic marine conditions.
        """
        ts_val = timestamp.timestamp() if isinstance(timestamp, datetime) else 0.0

        spatial_seed = math.sin(latitude * 0.1) + math.cos(longitude * 0.1)
        time_seed = math.sin(ts_val / 43200.0)  # 12-hour cycle

        curr_speed = round(0.45 + 0.15 * math.sin(spatial_seed + time_seed), 2)
        curr_dir = round((55.0 + 15.0 * math.cos(spatial_seed)) % 360.0, 1)

        wind_speed = round(13.0 + 4.0 * math.sin(time_seed * 1.5), 1)
        wind_dir = round((65.0 + 18.0 * math.sin(spatial_seed * 0.8)) % 360.0, 1)

        temp = round(-1.5 + 0.7 * math.cos(latitude * 0.05 + time_seed), 1)

        lat_factor = max(0.0, min(1.0, (-latitude - 60.0) / 20.0))
        sea_ice = round(max(0.20, min(0.95, 0.40 + 0.45 * lat_factor + 0.08 * math.sin(time_seed))), 2)

        return EnvironmentalCondition(
            current_speed=curr_speed,
            current_direction=curr_dir,
            wind_speed=wind_speed,
            wind_direction=wind_dir,
            temperature=temp,
            sea_ice_concentration=sea_ice
        )
