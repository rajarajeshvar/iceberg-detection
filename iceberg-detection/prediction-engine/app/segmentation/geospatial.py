import os
import re
from typing import Dict, Any, Optional, Tuple
import rasterio
from rasterio.transform import Affine
from rasterio.warp import transform

def parse_s1_filename(filename: str) -> Dict[str, Any]:
    """
    Parses Sentinel-1 SAR acquisition parameters and metadata encoded in standard filenames.
    """
    basename = os.path.basename(filename)
    stem = os.path.splitext(basename)[0]
    
    pattern = r"^(S1[AB])_([A-Z0-9]+)_([A-Z0-9]+)_([A-Z0-9]+)_([0-9]{8}T[0-9]{6})_([0-9]{8}T[0-9]{6})_([0-9A-F]+)_([0-9A-F]+)_([0-9A-F]+)_([0-9]+)_([0-9]+)_(.*)$"
    m = re.match(pattern, stem)
    
    if m:
        sat, mode, prod, pol_class, start_t, stop_t, orbit, datatake, uid, epsg, res_m, extra = m.groups()
        
        def to_iso(t_str):
            return f"{t_str[0:4]}-{t_str[4:6]}-{t_str[6:8]}T{t_str[9:11]}:{t_str[11:13]}:{t_str[13:15]}Z"
        
        polarization_str = "HH+HV" if "SDH" in pol_class or "DH" in pol_class else "VV+VH" if "SDV" in pol_class else "Dual-Pol SAR"
        
        return {
            "parsed": True,
            "sensor": f"Sentinel-1{sat[-1]}",
            "satellite": sat,
            "mode": mode,
            "product_type": prod,
            "polarization": polarization_str,
            "polarization_class": pol_class,
            "start_time": to_iso(start_t),
            "stop_time": to_iso(stop_t),
            "orbit_number": orbit,
            "datatake_id": datatake,
            "unique_id": uid,
            "native_epsg": f"EPSG:{epsg}",
            "nominal_resolution_m": float(res_m),
            "noise_filtering": extra
        }
    else:
        return {
            "parsed": False,
            "sensor": "Sentinel-1 SAR",
            "mode": "Unknown",
            "product_type": "GRD",
            "polarization": "Dual-Pol",
            "start_time": None,
            "stop_time": None,
            "native_epsg": None,
            "nominal_resolution_m": 40.0
        }

def pixel_to_projected(px: float, py: float, affine_transform: Affine) -> Tuple[float, float]:
    """Converts pixel coordinate (px, py) to projected coordinates (meters)."""
    proj_x, proj_y = rasterio.transform.xy(affine_transform, py, px)
    return proj_x, proj_y

def projected_to_geographic(
    proj_x: float, 
    proj_y: float, 
    source_crs: str = "EPSG:3996", 
    target_crs: str = "EPSG:4326"
) -> Tuple[float, float]:
    """Converts projected coordinates (meters) to WGS84 GPS degrees (Lat, Lon)."""
    try:
        lons, lats = transform(source_crs, target_crs, [proj_x], [proj_y])
        return float(lats[0]), float(lons[0])
    except Exception:
        return 0.0, 0.0

class CoordinateTransformer:
    """Stateful coordinate transformer for GeoTIFF imagery."""
    def __init__(self, affine_transform: Affine, source_crs: str = "EPSG:3996"):
        self.affine = affine_transform
        self.source_crs = str(source_crs) if source_crs else "EPSG:3996"
        
    def transform_pixel(self, px: float, py: float) -> Tuple[float, float, float, float]:
        proj_x, proj_y = pixel_to_projected(px, py, self.affine)
        lat, lon = projected_to_geographic(proj_x, proj_y, self.source_crs, "EPSG:4326")
        return proj_x, proj_y, lat, lon

def extract_tiff_metadata(filepath: str) -> Dict[str, Any]:
    """Extracts embedded GeoTIFF metadata, CRS, affine transform, and bounds."""
    filename_meta = parse_s1_filename(filepath)
    if not os.path.exists(filepath):
        return {"metadata_available": False, "filepath": filepath, **filename_meta}
        
    try:
        with rasterio.open(filepath) as src:
            has_crs = src.crs is not None
            has_transform = src.transform is not None
            crs_str = str(src.crs) if has_crs else "EPSG:3996"
            
            pixel_size_x = abs(src.transform[0]) if has_transform else 40.0
            pixel_size_y = abs(src.transform[4]) if has_transform else 40.0
            
            bounds_dict = {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top
            } if has_transform else None
            
            # WGS84 geographic bounds
            wgs84_bounds = None
            if has_crs and has_transform:
                try:
                    from rasterio.warp import transform_bounds
                    b = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                    wgs84_bounds = {"min_lon": b[0], "min_lat": b[1], "max_lon": b[2], "max_lat": b[3]}
                except Exception:
                    pass
            
            return {
                "metadata_available": has_crs and has_transform,
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "crs": crs_str,
                "transform": list(src.transform) if has_transform else None,
                "pixel_size_x_m": pixel_size_x,
                "pixel_size_y_m": pixel_size_y,
                "pixel_area_m2": pixel_size_x * pixel_size_y,
                "bounds": bounds_dict,
                "wgs84_bounds": wgs84_bounds,
                **filename_meta
            }
    except Exception as e:
        return {"metadata_available": False, "filepath": filepath, "error": str(e), **filename_meta}
