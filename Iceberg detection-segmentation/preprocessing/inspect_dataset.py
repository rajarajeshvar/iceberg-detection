import os
import glob
import json
import rasterio
import numpy as np
from typing import Dict, Any, List

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

def run_dataset_audit(
    imgs_dir: str = "S1UnetPlusPlus/imgs",
    masks_dir: str = "S1UnetPlusPlus/masks"
) -> Dict[str, Any]:
    """
    Performs complete audit of image-mask pairs, dimensions, CRS, data types, and iceberg pixel stats.
    """
    imgs_dir = resolve_path(imgs_dir)
    masks_dir = resolve_path(masks_dir)
    img_files = sorted([f for f in os.listdir(imgs_dir) if f.endswith(".tif")])
    mask_files = sorted([f for f in os.listdir(masks_dir) if f.endswith(".tif")])
    
    total_imgs = len(img_files)
    total_masks = len(mask_files)
    
    mask_set = set(mask_files)
    valid_pairs = []
    unpaired_images = []
    corrupted_files = []
    empty_masks = []
    
    total_iceberg_pixels = 0
    total_pixels = 0
    all_crs = set()
    all_resolutions = set()
    
    for img_name in img_files:
        stem = os.path.splitext(img_name)[0]
        expected_mask = f"{stem}_mask.tif"
        
        img_path = os.path.join(imgs_dir, img_name)
        mask_path = os.path.join(masks_dir, expected_mask)
        
        if expected_mask not in mask_set:
            unpaired_images.append(img_name)
            continue
            
        try:
            with rasterio.open(img_path) as src_i, rasterio.open(mask_path) as src_m:
                i_crs = str(src_i.crs)
                m_crs = str(src_m.crs)
                all_crs.add(i_crs)
                
                i_res = (abs(src_i.transform[0]), abs(src_i.transform[4]))
                all_resolutions.add(i_res)
                
                # Check dimension match
                if (src_i.width != src_m.width) or (src_i.height != src_m.height):
                    corrupted_files.append({"file": img_name, "reason": "Dimension mismatch between image and mask"})
                    continue
                    
                mask_arr = src_m.read(1)
                iceberg_px = int((mask_arr > 0).sum())
                total_iceberg_pixels += iceberg_px
                total_pixels += mask_arr.size
                
                if iceberg_px == 0:
                    empty_masks.append(img_name)
                    
                valid_pairs.append({
                    "image": img_name,
                    "mask": expected_mask,
                    "width": src_i.width,
                    "height": src_i.height,
                    "channels": src_i.count,
                    "crs": i_crs,
                    "resolution_m": i_res[0],
                    "iceberg_pixels": iceberg_px,
                    "iceberg_ratio": float(iceberg_px / mask_arr.size)
                })
        except Exception as e:
            corrupted_files.append({"file": img_name, "reason": str(e)})
            
    report = {
        "total_images": total_imgs,
        "total_masks": total_masks,
        "valid_pairs": len(valid_pairs),
        "unpaired_images": unpaired_images,
        "corrupted_files": corrupted_files,
        "empty_masks_count": len(empty_masks),
        "total_iceberg_pixels": total_iceberg_pixels,
        "total_pixels": total_pixels,
        "overall_iceberg_density": float(total_iceberg_pixels / total_pixels) if total_pixels > 0 else 0.0,
        "unique_crs": list(all_crs),
        "unique_resolutions": [list(r) for r in all_resolutions]
    }
    
    return report

if __name__ == "__main__":
    report = run_dataset_audit()
    print(json.dumps(report, indent=2))
