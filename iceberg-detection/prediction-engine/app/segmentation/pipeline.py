import os
import io
import base64
import numpy as np
import cv2
import torch
import rasterio
from rasterio.transform import Affine
from typing import Dict, Any, List, Optional, Tuple

from app.segmentation.model import SegFormerB0Iceberg
from app.segmentation.geospatial import CoordinateTransformer, extract_tiff_metadata

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

def encode_b64_png(img_arr: np.ndarray) -> str:
    """Encodes a uint8 image array (grayscale or BGR) to base64 PNG string."""
    _, buf = cv2.imencode(".png", img_arr)
    return base64.b64encode(buf).decode("utf-8")

def encode_gray_b64(gray: np.ndarray) -> str:
    arr = gray.copy()
    if np.issubdtype(arr.dtype, np.floating):
        uint8_arr = (np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8)
    else:
        uint8_arr = ((arr > 0).astype(np.uint8) * 255) if arr.max() <= 1 else arr.astype(np.uint8)
    return encode_b64_png(uint8_arr)

class SARIcebergSegmentationPipeline:
    """
    Production-grade inference pipeline for Sentinel-1 SAR Iceberg Segmentation.
    """
    def __init__(
        self,
        checkpoint_path: str = "models/segformer_best_model.pt",
        device: Optional[str] = None
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
            
        self.confidence_threshold = 0.50
        self.min_iceberg_pixels = 3
        self.morph_kernel = 3
        self.target_size = 512
        self.pixel_res_m = 40.0
        
        self.model = SegFormerB0Iceberg(num_classes=2).to(self.device)
        
        if os.path.exists(checkpoint_path):
            try:
                ckpt = torch.load(checkpoint_path, map_location=self.device)
                if "model_state_dict" in ckpt:
                    self.model.load_state_dict(ckpt["model_state_dict"])
                else:
                    self.model.load_state_dict(ckpt)
                print(f"[SegFormer] Loaded weights from {checkpoint_path}")
            except Exception as e:
                print(f"[SegFormer] Warning: Failed loading checkpoint {checkpoint_path}: {e}")
        else:
            print(f"[SegFormer] Warning: Checkpoint not found at {checkpoint_path}. Using base weights.")
            
        self.model.eval()

    def _clean_sar_array(self, raw_img: np.ndarray) -> np.ndarray:
        """Sanitizes SAR numpy array: cleans NaNs/Infs and normalizes to [0, 1]."""
        arr = np.nan_to_num(raw_img, nan=0.0, posinf=1.0, neginf=0.0).astype(np.float32)
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=0)
        elif arr.ndim == 3 and arr.shape[0] == 1:
            arr = np.repeat(arr, 3, axis=0)
        elif arr.ndim == 3 and arr.shape[0] == 2:
            # HH, HV -> HH, HV, (HH+HV)/2
            synth = (arr[0] + arr[1]) / 2.0
            arr = np.stack([arr[0], arr[1], synth], axis=0)
            
        # Normalize each channel into [0, 1] using robust percentile scaling
        for c in range(arr.shape[0]):
            ch = arr[c]
            p1, p99 = np.percentile(ch, 1), np.percentile(ch, 99)
            if p99 > p1:
                arr[c] = np.clip((ch - p1) / (p99 - p1), 0.0, 1.0)
            else:
                arr[c] = np.clip(ch, 0.0, 1.0)
                
        return arr

    @torch.no_grad()
    def predict_tiff(self, filepath: str) -> Dict[str, Any]:
        """
        Runs full segmentation, geospatial coordinate mapping, and iceberg extraction on a GeoTIFF.
        """
        meta = extract_tiff_metadata(filepath)
        filename = os.path.basename(filepath)
        
        with rasterio.open(filepath) as src:
            raw_data = src.read()
            affine_tf = src.transform
            crs_str = str(src.crs) if src.crs else "EPSG:3996"
            
        clean_img = self._clean_sar_array(raw_data)
        orig_h, orig_w = clean_img.shape[-2], clean_img.shape[-1]
        
        # Resize to 512x512 for optimal SegFormer receptive field
        img_512 = np.zeros((3, self.target_size, self.target_size), dtype=np.float32)
        for c in range(3):
            img_512[c] = cv2.resize(clean_img[c], (self.target_size, self.target_size), interpolation=cv2.INTER_LINEAR)
            
        # Normalize with ImageNet stats
        norm_img = (img_512 - IMAGENET_MEAN) / IMAGENET_STD
        input_tensor = torch.tensor(norm_img, dtype=torch.float32).unsqueeze(0).to(self.device)
        
        # Model inference
        prob_tensor = self.model.predict_probability(input_tensor)
        prob_512 = prob_tensor.squeeze(0).cpu().numpy()
        
        # Resize probability back to original raster dimensions
        prob_map = cv2.resize(prob_512, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        binary_mask = (prob_map >= self.confidence_threshold).astype(np.uint8)
        
        # Morphological filtering
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_kernel, self.morph_kernel))
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
        
        # Connected components extraction
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask)
        
        # Setup coordinate transformer
        transformer = CoordinateTransformer(affine_tf, source_crs=crs_str)
        timestamp_str = meta.get("start_time") or "2026-09-18T12:00:00Z"
        
        detected_icebergs = []
        valid_mask = np.zeros_like(binary_mask)
        
        ib_idx = 1
        for lbl in range(1, num_labels):
            area_px = int(stats[lbl, cv2.CC_STAT_AREA])
            if area_px < self.min_iceberg_pixels:
                continue
                
            valid_mask[labels == lbl] = 1
            x = int(stats[lbl, cv2.CC_STAT_LEFT])
            y = int(stats[lbl, cv2.CC_STAT_TOP])
            w = int(stats[lbl, cv2.CC_STAT_WIDTH])
            h = int(stats[lbl, cv2.CC_STAT_HEIGHT])
            cx, cy = float(centroids[lbl][0]), float(centroids[lbl][1])
            
            # Extract GPS and projected coordinates
            proj_x, proj_y, lat, lon = transformer.transform_pixel(cx, cy)
            
            # Calculate physical dimensions
            pixel_area = float(meta.get("pixel_area_m2", 1600.0))
            pixel_res = float(meta.get("pixel_size_x_m", 40.0))
            area_m2 = area_px * pixel_area
            area_km2 = area_m2 / 1e6
            length_m = max(w, h) * pixel_res
            width_m  = min(w, h) * pixel_res
            
            # Mean confidence over iceberg mask
            component_mask = (labels == lbl)
            conf_val = float(np.mean(prob_map[component_mask]))
            
            iceberg_id = f"IB-S1-{ib_idx:03d}"
            ib_idx += 1
            
            detected_icebergs.append({
                "iceberg_id": iceberg_id,
                "timestamp": timestamp_str,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "projected_x": round(proj_x, 2),
                "projected_y": round(proj_y, 2),
                "area_pixels": area_px,
                "area_m2": round(area_m2, 1),
                "area_km2": round(area_km2, 4),
                "length_m": round(length_m, 1),
                "width_m": round(width_m, 1),
                "size_m": round(max(length_m, width_m), 1),
                "confidence": round(conf_val, 4),
                "bounding_box": {
                    "x_min": x,
                    "y_min": y,
                    "x_max": x + w,
                    "y_max": y + h
                },
                "centroid_pixel": {
                    "x": round(cx, 2),
                    "y": round(cy, 2)
                },
                "sensor": meta.get("sensor", "Sentinel-1"),
                "polarization": meta.get("polarization", "Dual-Pol")
            })
            
        # Build Visual Overlay Image
        base_display = (np.clip(clean_img[0], 0, 1) * 255).astype(np.uint8)
        base_bgr = cv2.cvtColor(base_display, cv2.COLOR_GRAY2BGR)
        overlay = base_bgr.copy()
        
        # Colorize iceberg mask with cyan highlight
        mask_bool = valid_mask > 0
        overlay[mask_bool] = (0.2 * overlay[mask_bool] + 0.8 * np.array([255, 230, 0])).astype(np.uint8)
        
        for ib in detected_icebergs:
            bb = ib["bounding_box"]
            cv2.rectangle(overlay, (bb["x_min"], bb["y_min"]), (bb["x_max"], bb["y_max"]), (0, 255, 0), 1)
            cx, cy = int(ib["centroid_pixel"]["x"]), int(ib["centroid_pixel"]["y"])
            cv2.circle(overlay, (cx, cy), 2, (0, 0, 255), -1)
            cv2.putText(
                overlay,
                ib["iceberg_id"],
                (bb["x_min"], max(10, bb["y_min"] - 2)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 255, 255),
                1,
                cv2.LINE_AA
            )
            
        return {
            "filename": filename,
            "metadata": meta,
            "total_detected": len(detected_icebergs),
            "icebergs": detected_icebergs,
            "has_detections": len(detected_icebergs) > 0,
            "images": {
                "sar": encode_gray_b64(base_display),
                "probability_map": encode_gray_b64(prob_map),
                "predicted_mask": encode_gray_b64(valid_mask),
                "overlay": encode_b64_png(overlay)
            }
        }
