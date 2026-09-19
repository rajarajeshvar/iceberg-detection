import numpy as np
from typing import Tuple, Dict, Any, Optional

def validate_and_clean_sample(
    image_arr: np.ndarray,
    mask_arr: np.ndarray
) -> Tuple[bool, Optional[np.ndarray], Optional[np.ndarray], Dict[str, Any]]:
    """
    Validates, cleans, and standardizes an image-mask sample for training/inference.
    
    Rules:
    1. Image must be 3-channel (C, H, W) or (H, W, C) -> converted to (C, H, W).
    2. Mask must be 1-channel -> converted to (1, H, W) with binary values {0, 1}.
    3. NaNs / Infs in image are safely filled with 0.0 (radar noise floor).
    4. Image pixel values clamped to [0.0, 1.0].
    5. Mask values strictly binarized: >0 -> 1, <=0 -> 0.
    
    Returns:
        is_valid: bool
        clean_img: np.ndarray (3, H, W) float32
        clean_mask: np.ndarray (1, H, W) int64
        qc_metadata: Dict
    """
    qc_info = {
        "nan_replaced": 0,
        "inf_replaced": 0,
        "clamped": False,
        "valid": True,
        "rejection_reason": None
    }
    
    # Check shape
    if image_arr.ndim == 2:
        image_arr = np.expand_dims(image_arr, 0)
        image_arr = np.repeat(image_arr, 3, axis=0)
    elif image_arr.ndim == 3 and image_arr.shape[2] == 3 and image_arr.shape[0] != 3:
        image_arr = np.transpose(image_arr, (2, 0, 1))
        
    if mask_arr.ndim == 2:
        mask_arr = np.expand_dims(mask_arr, 0)
    elif mask_arr.ndim == 3 and mask_arr.shape[2] == 1 and mask_arr.shape[0] != 1:
        mask_arr = np.transpose(mask_arr, (2, 0, 1))
        
    if image_arr.shape[0] != 3 or image_arr.shape[1] != mask_arr.shape[1] or image_arr.shape[2] != mask_arr.shape[2]:
        qc_info["valid"] = False
        qc_info["rejection_reason"] = f"Shape mismatch: img {image_arr.shape} vs mask {mask_arr.shape}"
        return False, None, None, qc_info
        
    # Replace NaNs / Infs in image
    nan_count = int(np.isnan(image_arr).sum())
    inf_count = int(np.isinf(image_arr).sum())
    qc_info["nan_replaced"] = nan_count
    qc_info["inf_replaced"] = inf_count
    
    clean_img = np.nan_to_num(image_arr, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)
    
    # Normalize / clamp to [0.0, 1.0] if needed
    if clean_img.max() > 1.0 or clean_img.min() < 0.0:
        clean_img = np.clip(clean_img, 0.0, 1.0)
        qc_info["clamped"] = True
        
    # Binarize mask
    clean_mask = (mask_arr > 0).astype(np.int64)
    
    return True, clean_img, clean_mask, qc_info
