from typing import Dict, Any, List, Optional
import numpy as np
import cv2
from rasterio.transform import Affine
from .coordinates import CoordinateTransformer

def compute_iceberg_geometric_features(
    contour: np.ndarray,
    binary_mask_component: np.ndarray,
    prob_map: np.ndarray,
    pixel_size_m: float = 40.0,
    transformer: Optional[CoordinateTransformer] = None
) -> Dict[str, Any]:
    """
    Computes rigorous geometric, physical, and geospatial measurements for an individual iceberg object.
    
    Parameters:
        contour: (N, 1, 2) numpy array of contour vertices from cv2.findContours
        binary_mask_component: 2D uint8 binary mask of this component
        prob_map: 2D float32 probability map from SegFormer
        pixel_size_m: Spatial resolution per pixel (e.g. 40.0m)
        transformer: Optional CoordinateTransformer instance for geospatial projections
    """
    # 1. Pixel-based area and perimeter
    area_pixels = int(np.sum(binary_mask_component > 0))
    perimeter_pixels = float(cv2.arcLength(contour, closed=True))
    
    # 2. Moments & Centroid
    M = cv2.moments(binary_mask_component.astype(np.uint8))
    if M["m00"] > 0:
        cx_px = float(M["m10"] / M["m00"])
        cy_px = float(M["m01"] / M["m00"])
    else:
        # Fallback to bounding box center
        x, y, w, h = cv2.boundingRect(contour)
        cx_px = float(x + w / 2.0)
        cy_px = float(y + h / 2.0)
        
    # 3. Axis-Aligned Bounding Box (pixels)
    bx, by, bw, bh = cv2.boundingRect(contour)
    bbox_dict = {
        "x_min": int(bx),
        "y_min": int(by),
        "x_max": int(bx + bw),
        "y_max": int(by + bh)
    }
    
    # 4. Minimum-Area Rotated Bounding Box (Length, Width, Orientation)
    # cv2.minAreaRect returns ((cx, cy), (width, height), angle_deg)
    rect = cv2.minAreaRect(contour)
    (rect_cx, rect_cy), (dim1, dim2), angle = rect
    
    length_px = max(dim1, dim2)
    width_px = min(dim1, dim2)
    
    # Standardize orientation angle in degrees [-90, 90]
    orientation_deg = float(angle)
    
    # 5. Physical Metric Calculations
    pixel_area_m2 = pixel_size_m * pixel_size_m  # 40m * 40m = 1600 m²
    area_m2 = float(area_pixels * pixel_area_m2)
    area_km2 = float(area_m2 / 1_000_000.0)
    
    perimeter_m = float(perimeter_pixels * pixel_size_m)
    length_m = float(length_px * pixel_size_m)
    width_m = float(width_px * pixel_size_m)
    
    # Shape Descriptors
    # Circularity = 4 * pi * Area / (Perimeter^2)
    circularity = float(4.0 * np.pi * area_pixels / (perimeter_pixels**2)) if perimeter_pixels > 0 else 0.0
    aspect_ratio = float(length_px / width_px) if width_px > 0 else 1.0
    
    # 6. Mean Segmentation Confidence over the iceberg mask
    mask_bool = binary_mask_component > 0
    seg_confidence = float(np.mean(prob_map[mask_bool])) if np.any(mask_bool) else 0.0
    
    # 7. Geospatial coordinates (if transformer available)
    if transformer is not None:
        proj_x, proj_y, lat, lon = transformer.transform_pixel(cx_px, cy_px)
        geo_info = {
            "metadata_available": True,
            "projected_x": float(proj_x),
            "projected_y": float(proj_y),
            "latitude": float(lat),
            "longitude": float(lon),
            "crs": transformer.source_crs
        }
    else:
        geo_info = {
            "metadata_available": False,
            "projected_x": None,
            "projected_y": None,
            "latitude": None,
            "longitude": None,
            "crs": None
        }
        
    return {
        "centroid_pixel": {"x": round(cx_px, 2), "y": round(cy_px, 2)},
        "bounding_box": bbox_dict,
        "area_pixels": area_pixels,
        "area_m2": round(area_m2, 2),
        "area_km2": round(area_km2, 6),
        "perimeter_pixels": round(perimeter_pixels, 2),
        "perimeter_m": round(perimeter_m, 2),
        "length_m": round(length_m, 2),
        "width_m": round(width_m, 2),
        "length_px": round(length_px, 2),
        "width_px": round(width_px, 2),
        "orientation_deg": round(orientation_deg, 2),
        "circularity": round(circularity, 4),
        "aspect_ratio": round(aspect_ratio, 3),
        "segmentation_confidence": round(seg_confidence, 4),
        **geo_info
    }
