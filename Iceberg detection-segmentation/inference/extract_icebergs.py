import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from geospatial.coordinates import CoordinateTransformer
from geospatial.measurements import compute_iceberg_geometric_features

def extract_individual_icebergs(
    prob_map: np.ndarray,
    confidence_threshold: float = 0.5,
    min_pixels: int = 4,
    morph_kernel_size: int = 3,
    pixel_size_m: float = 40.0,
    transformer: Optional[CoordinateTransformer] = None,
    sample_prefix: str = "IB"
) -> List[Dict[str, Any]]:
    """
    Extracts individual iceberg objects from a 2D probability map using:
    1. Confidence thresholding -> binary mask
    2. Morphological closing to seal internal voids
    3. Connected Component Analysis / Contour detection
    4. Per-iceberg geometric and geospatial feature computation.
    
    Parameters:
        prob_map: (H, W) float32 array in [0.0, 1.0]
        confidence_threshold: Classification probability threshold
        min_pixels: Filter out noise blobs below this pixel area
        morph_kernel_size: Size of morphological structuring element
        pixel_size_m: Physical resolution per pixel (meters)
        transformer: CoordinateTransformer instance for CRS transforms
        sample_prefix: Prefix for local iceberg IDs
    """
    # 1. Binarize
    binary_mask = (prob_map >= confidence_threshold).astype(np.uint8)
    
    # 2. Morphological cleanup: closing to fill small holes
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
    cleaned_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
    
    # 3. Find connected contours
    contours, hierarchy = cv2.findContours(
        cleaned_mask, 
        cv2.RETR_EXTERNAL, 
        cv2.CHAIN_APPROX_SIMPLE
    )
    
    detected_icebergs = []
    iceberg_idx = 1
    
    for cnt in contours:
        # Create single object binary mask
        obj_mask = np.zeros_like(cleaned_mask)
        cv2.drawContours(obj_mask, [cnt], -1, 1, thickness=-1)
        
        area_px = int(np.sum(obj_mask))
        if area_px < min_pixels:
            continue
            
        # Calculate full geometric and geospatial metrics
        features = compute_iceberg_geometric_features(
            contour=cnt,
            binary_mask_component=obj_mask,
            prob_map=prob_map,
            pixel_size_m=pixel_size_m,
            transformer=transformer
        )
        
        iceberg_id = f"{sample_prefix}_{iceberg_idx:04d}"
        features["iceberg_id"] = iceberg_id
        
        detected_icebergs.append(features)
        iceberg_idx += 1
        
    return detected_icebergs
