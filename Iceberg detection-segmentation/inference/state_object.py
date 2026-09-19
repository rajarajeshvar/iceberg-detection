from typing import Dict, Any, List, Optional
import json

def build_iceberg_state_object(
    iceberg_features: Dict[str, Any],
    source_metadata: Dict[str, Any],
    source_image_name: str
) -> Dict[str, Any]:
    """
    Builds a standardized Iceberg State Object adhering to the project schema.
    If geospatial metadata is available, populates valid coordinates, CRS, physical dimensions,
    and acquisition context. If unavailable, outputs metadata_available = False without fabricating data.
    """
    has_meta = iceberg_features.get("metadata_available", False) and source_metadata.get("metadata_available", False)
    
    state_obj = {
        "iceberg_id": iceberg_features.get("iceberg_id", "IB_0001"),
        "source_image": source_image_name,
        "metadata_available": bool(has_meta),
        "timestamp": source_metadata.get("start_time") if has_meta else None,
        
        # Geospatial coordinates
        "latitude": iceberg_features.get("latitude") if has_meta else None,
        "longitude": iceberg_features.get("longitude") if has_meta else None,
        "projected_x": iceberg_features.get("projected_x") if has_meta else None,
        "projected_y": iceberg_features.get("projected_y") if has_meta else None,
        "crs": iceberg_features.get("crs") if has_meta else None,
        
        # Dimensions & Shape
        "area_pixels": iceberg_features.get("area_pixels", 0),
        "area_m2": iceberg_features.get("area_m2") if has_meta else None,
        "area_km2": iceberg_features.get("area_km2") if has_meta else None,
        
        "perimeter_pixels": iceberg_features.get("perimeter_pixels", 0.0),
        "perimeter_m": iceberg_features.get("perimeter_m") if has_meta else None,
        
        "length_m": iceberg_features.get("length_m") if has_meta else None,
        "width_m": iceberg_features.get("width_m") if has_meta else None,
        "length_px": iceberg_features.get("length_px", 0.0),
        "width_px": iceberg_features.get("width_px", 0.0),
        
        "orientation_deg": iceberg_features.get("orientation_deg", 0.0),
        "circularity": iceberg_features.get("circularity", 0.0),
        "aspect_ratio": iceberg_features.get("aspect_ratio", 1.0),
        
        # Bounding box & Centroid
        "bounding_box": iceberg_features.get("bounding_box", {}),
        "centroid_pixel": iceberg_features.get("centroid_pixel", {}),
        
        # Model certainty & Acquisition info
        "segmentation_confidence": iceberg_features.get("segmentation_confidence", 0.0),
        "sensor": source_metadata.get("sensor", "Sentinel-1"),
        "mode": source_metadata.get("mode", "EW"),
        "polarization": source_metadata.get("polarization", "HH+HV"),
        "orbit_number": source_metadata.get("orbit_number"),
        "datatake_id": source_metadata.get("datatake_id")
    }
    
    return state_obj

def generate_iceberg_states_document(
    detected_icebergs: List[Dict[str, Any]],
    source_metadata: Dict[str, Any],
    source_image_name: str
) -> Dict[str, Any]:
    """
    Generates a full machine-readable JSON document containing scene-level context
    and an array of Iceberg State Objects for future trajectory tracking modules.
    """
    states = [
        build_iceberg_state_object(ib, source_metadata, source_image_name)
        for ib in detected_icebergs
    ]
    
    document = {
        "scene_name": source_image_name,
        "total_icebergs_detected": len(states),
        "acquisition_timestamp": source_metadata.get("start_time"),
        "sensor": source_metadata.get("sensor", "Sentinel-1"),
        "mode": source_metadata.get("mode", "EW"),
        "native_crs": source_metadata.get("crs", "EPSG:3996"),
        "pixel_resolution_m": source_metadata.get("pixel_size_x_m", 40.0),
        "iceberg_states": states
    }
    
    return document
