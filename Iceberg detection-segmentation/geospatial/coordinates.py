from typing import Tuple, Optional, List
import rasterio
from rasterio.transform import Affine
from rasterio.warp import transform

def pixel_to_projected(
    px: float, 
    py: float, 
    affine_transform: Affine
) -> Tuple[float, float]:
    """
    Converts (x, y) column/row pixel coordinates to projected coordinates (meters)
    using the affine geotransform.
    """
    proj_x, proj_y = rasterio.transform.xy(affine_transform, py, px)
    return proj_x, proj_y

def projected_to_geographic(
    proj_x: float, 
    proj_y: float, 
    source_crs: str = "EPSG:3996", 
    target_crs: str = "EPSG:4326"
) -> Tuple[float, float]:
    """
    Converts projected coordinates (meters) to geographic coordinates (Latitude, Longitude in degrees)
    via proper geospatial coordinate reference system transformation.
    """
    lons, lats = transform(source_crs, target_crs, [proj_x], [proj_y])
    return lats[0], lons[0]

class CoordinateTransformer:
    """
    Stateful coordinate transformer for a specific GeoTIFF scene.
    """
    def __init__(self, affine_transform: Affine, source_crs: str = "EPSG:3996"):
        self.affine = affine_transform
        self.source_crs = source_crs
        
    def transform_pixel(self, px: float, py: float) -> Tuple[float, float, float, float]:
        """
        Transforms a pixel coordinate (px, py) to (projected_x, projected_y, latitude, longitude).
        """
        proj_x, proj_y = pixel_to_projected(px, py, self.affine)
        lat, lon = projected_to_geographic(proj_x, proj_y, self.source_crs, "EPSG:4326")
        return proj_x, proj_y, lat, lon
