import math
from typing import List, Tuple, Dict, Any
from app.utils.geo import haversine_distance


class NavigationalGrid:
    """
    Geospatial navigational grid covering Antarctic maritime sectors.
    Computes cell traversal costs based on distance, sea-ice density, and proximity to iceberg hazards.
    """

    def __init__(
        self,
        min_lat: float = -75.0,
        max_lat: float = -60.0,
        min_lon: float = 30.0,
        max_lon: float = 160.0,
        resolution_deg: float = 0.25
    ):
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon
        self.resolution_deg = resolution_deg

    def get_neighbors(self, node: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Get 8-directional spatial grid neighbors.
        """
        lat, lon = node
        neighbors = []
        step = self.resolution_deg

        for d_lat in [-step, 0.0, step]:
            for d_lon in [-step, 0.0, step]:
                if d_lat == 0.0 and d_lon == 0.0:
                    continue
                n_lat = round(lat + d_lat, 4)
                n_lon = round(lon + d_lon, 4)

                if self.min_lat <= n_lat <= self.max_lat and self.min_lon <= n_lon <= self.max_lon:
                    neighbors.append((n_lat, n_lon))

        return neighbors

    def calculate_cell_cost(
        self,
        from_node: Tuple[float, float],
        to_node: Tuple[float, float],
        iceberg_hazards: List[Dict[str, Any]],
        safety_weight: float = 0.5,
        fuel_weight: float = 0.5,
        sea_ice_concentration: float = 0.5
    ) -> float:
        """
        Compute edge traversal cost between adjacent grid cells.
        """
        dist_km = haversine_distance(from_node[0], from_node[1], to_node[0], to_node[1])

        # Fuel cost component (distance + sea ice resistance)
        ice_resistance_factor = 1.0 + 1.2 * (sea_ice_concentration ** 2)
        fuel_cost = dist_km * ice_resistance_factor

        # Safety hazard penalty (proximity to predicted iceberg positions & uncertainty circles)
        safety_hazard_penalty = 0.0

        for hazard in iceberg_hazards:
            h_lat = hazard["latitude"]
            h_lon = hazard["longitude"]
            radius_km = hazard.get("uncertainty_radius_km", 5.0)

            d_to_hazard = haversine_distance(to_node[0], to_node[1], h_lat, h_lon)

            # High penalty inside danger zone, decaying smoothly outside
            if d_to_hazard < radius_km:
                safety_hazard_penalty += 350.0 / max(0.5, d_to_hazard)
            elif d_to_hazard < radius_km + 25.0:
                safety_hazard_penalty += 80.0 / max(1.0, (d_to_hazard - radius_km + 1.0))

        total_cost = (fuel_weight * fuel_cost) + (safety_weight * safety_hazard_penalty)
        return max(0.1, total_cost)
