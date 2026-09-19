import os
import re
from typing import Dict, Any, Optional
import rasterio

def parse_s1_filename(filename: str) -> Dict[str, Any]:
    """
    Parses Sentinel-1 SAR acquisition parameters and metadata encoded in standard filenames.
    Example filename:
    S1A_EW_GRDM_1SDH_20160607T191602_20160607T191702_011609_011BF1_E168_3996_40_rm_thermal_noise_hvTrue_rm_texture_noise_hvTrue_25WES_2_2__ID24.tif
    """
    basename = os.path.basename(filename)
    stem = os.path.splitext(basename)[0]
    
    pattern = r"^(S1[AB])_([A-Z0-9]+)_([A-Z0-9]+)_([A-Z0-9]+)_([0-9]{8}T[0-9]{6})_([0-9]{8}T[0-9]{6})_([0-9A-F]+)_([0-9A-F]+)_([0-9A-F]+)_([0-9]+)_([0-9]+)_(.*)$"
    m = re.match(pattern, stem)
    
    if m:
        sat, mode, prod, pol_class, start_t, stop_t, orbit, datatake, uid, epsg, res_m, extra = m.groups()
        
        # Format timestamps into ISO format
        def to_iso(t_str):
            # 20160607T191602 -> 2016-06-07T19:16:02Z
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

def extract_tiff_metadata(filepath: str) -> Dict[str, Any]:
    """
    Extracts embedded GeoTIFF geospatial metadata, CRS, GeoTransform, bounds, and acquisition parameters.
    """
    filename_meta = parse_s1_filename(filepath)
    
    if not os.path.exists(filepath):
        return {
            "metadata_available": False,
            "filepath": filepath,
            "error": "File does not exist",
            **filename_meta
        }
        
    try:
        with rasterio.open(filepath) as src:
            has_crs = src.crs is not None
            has_transform = src.transform is not None
            
            crs_str = str(src.crs) if has_crs else None
            bounds_dict = {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top
            } if has_transform else None
            
            pixel_size_x = abs(src.transform[0]) if has_transform else 40.0
            pixel_size_y = abs(src.transform[4]) if has_transform else 40.0
            
            return {
                "metadata_available": has_crs and has_transform,
                "filepath": filepath,
                "filename": os.path.basename(filepath),
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "dtypes": [str(d) for d in src.dtypes],
                "crs": crs_str,
                "transform": list(src.transform) if has_transform else None,
                "pixel_size_x_m": pixel_size_x,
                "pixel_size_y_m": pixel_size_y,
                "pixel_area_m2": pixel_size_x * pixel_size_y,
                "bounds": bounds_dict,
                "driver": src.driver,
                "tags": dict(src.tags()),
                **filename_meta
            }
    except Exception as e:
        return {
            "metadata_available": False,
            "filepath": filepath,
            "error": str(e),
            **filename_meta
        }
