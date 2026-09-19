import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import yaml
import json
import torch
import cv2
import numpy as np
import rasterio

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

from inference.predict import SARIcebergInferencePipeline
from geospatial.metadata import extract_tiff_metadata

def run_test_set_eval_and_exports():
    """
    Runs the trained model on all 35 test GeoTIFF images, exports:
    - predicted binary masks to outputs/predictions/
    - visual 4-way overlays to outputs/overlays/
    - IcebergState JSON files to outputs/iceberg_states/
    """
    pipeline = SARIcebergInferencePipeline(
        checkpoint_path="outputs/checkpoints/best_model.pt",
        config_path="config.yaml"
    )
    
    pred_dir = resolve_path("outputs/predictions")
    overlay_dir = resolve_path("outputs/overlays")
    states_dir = resolve_path("outputs/iceberg_states")
    
    os.makedirs(pred_dir, exist_ok=True)
    os.makedirs(overlay_dir, exist_ok=True)
    os.makedirs(states_dir, exist_ok=True)
    
    # Load test dataset
    test_npz_path = resolve_path("data/processed/test.npz")
    test_npz = np.load(test_npz_path)
    test_imgs = test_npz["images"]
    test_masks = test_npz["masks"]
    
    # Load raw TIFF filenames for mapping
    raw_imgs_dir = resolve_path("S1UnetPlusPlus/imgs")
    raw_files = sorted([f for f in os.listdir(raw_imgs_dir) if f.endswith(".tif")]) if os.path.exists(raw_imgs_dir) else []
    
    print(f"Running full export on {len(test_imgs)} test scenes...")
    
    summary_results = []
    total_icebergs_all_scenes = 0
    
    for idx in range(len(test_imgs)):
        img_arr = test_imgs[idx]
        gt_mask = test_masks[idx, 0]
        
        # Find corresponding raw TIFF if possible
        sample_name = raw_files[idx % len(raw_files)]
        raw_path = os.path.join(raw_imgs_dir, sample_name)
        
        if os.path.exists(raw_path):
            with rasterio.open(raw_path) as src:
                tf = src.transform
                crs_str = str(src.crs) if src.crs else "EPSG:3996"
            meta = extract_tiff_metadata(raw_path)
            res = pipeline.predict_array(
                image_arr=img_arr,
                affine_transform=tf,
                source_crs=crs_str,
                metadata=meta,
                image_name=sample_name
            )
        else:
            res = pipeline.predict_array(
                image_arr=img_arr,
                source_crs="EPSG:3996",
                image_name=f"test_sample_{idx:03d}"
            )
        
        pred_mask = res["binary_mask"]
        prob_map = res["probability_map"]
        overlay_bgr = res["overlay_bgr"]
        icebergs = res["icebergs"]
        states_doc = res["iceberg_states_document"]
        
        total_icebergs_all_scenes += len(icebergs)
        
        # Save predicted mask PNG
        mask_out_path = os.path.join(pred_dir, f"test_{idx:03d}_pred_mask.png")
        cv2.imwrite(mask_out_path, pred_mask * 255)
        
        # Save visual comparison grid (Original SAR | GT Mask | Pred Mask | Overlay)
        sar_view = (np.clip(img_arr[0], 0, 1) * 255).astype(np.uint8)
        sar_bgr = cv2.cvtColor(sar_view, cv2.COLOR_GRAY2BGR)
        gt_bgr = cv2.cvtColor((gt_mask * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        pred_bgr = cv2.cvtColor((pred_mask * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
        
        top_row = np.hstack([sar_bgr, gt_bgr])
        bot_row = np.hstack([pred_bgr, overlay_bgr])
        grid = np.vstack([top_row, bot_row])
        
        overlay_out_path = os.path.join(overlay_dir, f"test_{idx:03d}_comparison.png")
        cv2.imwrite(overlay_out_path, grid)
        
        # Save IcebergState JSON
        json_out_path = os.path.join(states_dir, f"test_{idx:03d}_states.json")
        with open(json_out_path, "w") as jf:
            json.dump(states_doc, jf, indent=2)
            
        summary_results.append({
            "test_index": idx,
            "detected_icebergs": len(icebergs),
            "ground_truth_pixels": int(gt_mask.sum()),
            "predicted_pixels": int(pred_mask.sum()),
            "json_path": json_out_path
        })
        
    print(f"Export completed: {len(test_imgs)} test scenes processed, {total_icebergs_all_scenes} total iceberg objects extracted.")
    return summary_results

if __name__ == "__main__":
    run_test_set_eval_and_exports()
