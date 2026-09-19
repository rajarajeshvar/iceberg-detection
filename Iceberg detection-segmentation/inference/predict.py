import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import yaml
import json
import torch
import cv2
import numpy as np
import rasterio
from rasterio.transform import Affine
from typing import Dict, Any, List, Optional, Tuple, Union

try:
    from path_utils import PROJECT_ROOT, resolve_path
except ImportError:
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from path_utils import PROJECT_ROOT, resolve_path

from models.segformer import SegFormerB0Iceberg
from geospatial.metadata import extract_tiff_metadata
from geospatial.coordinates import CoordinateTransformer
from inference.extract_icebergs import extract_individual_icebergs
from inference.state_object import generate_iceberg_states_document
from preprocessing.quality_control import validate_and_clean_sample

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

class SARIcebergInferencePipeline:
    """
    Production-ready inference pipeline for Sentinel-1 SAR Iceberg Detection and Segmentation.
    """
    def __init__(
        self, 
        checkpoint_path: str = "outputs/checkpoints/best_model.pt",
        config_path: str = "config.yaml",
        device: Optional[str] = None
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
            
        resolved_config = resolve_path(config_path)
        with open(resolved_config, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            
        self.confidence_threshold = 0.50
        self.min_iceberg_pixels = self.config.get("inference", {}).get("min_iceberg_pixels", 2)
        self.morph_kernel = self.config.get("inference", {}).get("morphology_kernel_size", 3)
        self.pixel_res_m = self.config.get("data", {}).get("pixel_resolution_m", 40.0)
        self.target_size = 512
        
        # Load Model
        self.model = SegFormerB0Iceberg(
            num_classes=self.config.get("model", {}).get("num_classes", 2),
            pretrained_model_name=self.config.get("model", {}).get("backbone", "nvidia/mit-b0")
        ).to(self.device)
        
        resolved_ckpt = resolve_path(checkpoint_path)
        if os.path.exists(resolved_ckpt):
            checkpoint = torch.load(resolved_ckpt, map_location=self.device)
            if "model_state_dict" in checkpoint:
                self.model.load_state_dict(checkpoint["model_state_dict"])
            else:
                self.model.load_state_dict(checkpoint)
            print(f"Loaded optimized SegFormer-B0 weights from {resolved_ckpt}")
        else:
            print(f"Warning: Checkpoint '{resolved_ckpt}' not found. Using untrained weights.")
            
        self.model.eval()

    @torch.no_grad()
    def predict_array(
        self, 
        image_arr: np.ndarray,
        affine_transform: Optional[Affine] = None,
        source_crs: str = "EPSG:3996",
        metadata: Optional[Dict[str, Any]] = None,
        image_name: str = "sample_image.tif"
    ) -> Dict[str, Any]:
        """
        Runs inference on a numpy SAR array (3, H, W).
        """
        # QC / Clean
        orig_h, orig_w = image_arr.shape[-2], image_arr.shape[-1]
        dummy_mask = np.zeros((1, orig_h, orig_w), dtype=np.int64)
        valid, clean_img, _, qc_info = validate_and_clean_sample(image_arr, dummy_mask)
        
        if not valid:
            raise ValueError(f"Invalid input image: {qc_info.get('rejection_reason')}")
            
        # Resize to 512x512 for high-resolution transformer receptive field
        img_512 = np.zeros((3, self.target_size, self.target_size), dtype=np.float32)
        for c in range(3):
            img_512[c] = cv2.resize(clean_img[c], (self.target_size, self.target_size), interpolation=cv2.INTER_LINEAR)
            
        # ImageNet normalization alignment
        norm_img = (img_512 - IMAGENET_MEAN) / IMAGENET_STD
        
        # Model forward
        input_tensor = torch.tensor(norm_img, dtype=torch.float32).unsqueeze(0).to(self.device)
        prob_tensor = self.model.predict_probability(input_tensor)
        prob_512 = prob_tensor.squeeze(0).cpu().numpy()  # (512, 512)
        
        # Interpolate back to original resolution
        prob_map = cv2.resize(prob_512, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        
        # Binary segmentation mask
        binary_mask = (prob_map >= self.confidence_threshold).astype(np.uint8)
        
        # Post processing: Morphological close & Connected component filter
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_kernel, self.morph_kernel))
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
        
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask)
        for lbl in range(1, num_labels):
            if stats[lbl, cv2.CC_STAT_AREA] < self.min_iceberg_pixels:
                binary_mask[labels == lbl] = 0
        
        # Setup Coordinate Transformer if geotransform available
        transformer = None
        if affine_transform is not None:
            transformer = CoordinateTransformer(affine_transform, source_crs=source_crs)
            
        if metadata is None:
            metadata = {
                "metadata_available": transformer is not None,
                "sensor": "Sentinel-1 SAR",
                "mode": "EW",
                "polarization": "Dual-Pol",
                "crs": source_crs if transformer else None,
                "pixel_size_x_m": self.pixel_res_m
            }
            
        # Extract individual iceberg objects
        icebergs = extract_individual_icebergs(
            prob_map=prob_map,
            confidence_threshold=self.confidence_threshold,
            min_pixels=self.min_iceberg_pixels,
            morph_kernel_size=self.morph_kernel,
            pixel_size_m=self.pixel_res_m,
            transformer=transformer,
            sample_prefix="IB"
        )
        
        # Generate Iceberg State Object document
        states_doc = generate_iceberg_states_document(
            detected_icebergs=icebergs,
            source_metadata=metadata,
            source_image_name=image_name
        )
        
        # Generate Visual RGB Overlay
        # Use first channel or composite for base display
        base_display = (np.clip(clean_img[0], 0, 1) * 255).astype(np.uint8)
        base_bgr = cv2.cvtColor(base_display, cv2.COLOR_GRAY2BGR)
        
        overlay = base_bgr.copy()
        # Tint iceberg pixels red/cyan
        mask_bool = binary_mask > 0
        overlay[mask_bool] = (0.3 * overlay[mask_bool] + 0.7 * np.array([0, 255, 255])).astype(np.uint8)
        
        # Draw bounding boxes and centroids
        for ib in icebergs:
            bbox = ib["bounding_box"]
            cv2.rectangle(
                overlay, 
                (bbox["x_min"], bbox["y_min"]), 
                (bbox["x_max"], bbox["y_max"]), 
                (0, 255, 0), 
                1
            )
            cx, cy = int(ib["centroid_pixel"]["x"]), int(ib["centroid_pixel"]["y"])
            cv2.circle(overlay, (cx, cy), 2, (0, 0, 255), -1)
            cv2.putText(
                overlay, 
                ib["iceberg_id"], 
                (bbox["x_min"], max(10, bbox["y_min"] - 3)), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.35, 
                (255, 255, 255), 
                1
            )
            
        return {
            "image_name": image_name,
            "probability_map": prob_map,
            "binary_mask": binary_mask,
            "overlay_bgr": overlay,
            "icebergs": icebergs,
            "iceberg_states_document": states_doc,
            "total_detected": len(icebergs),
            "qc_info": qc_info
        }

    def predict_tiff(self, tiff_path: str) -> Dict[str, Any]:
        """
        Runs full inference pipeline directly on a Sentinel-1 SAR GeoTIFF file.
        """
        if not os.path.exists(tiff_path):
            raise FileNotFoundError(f"TIFF file not found: {tiff_path}")
            
        meta = extract_tiff_metadata(tiff_path)
        with rasterio.open(tiff_path) as src:
            arr = src.read()
            tf = src.transform
            crs_str = str(src.crs) if src.crs else "EPSG:3996"
            
        return self.predict_array(
            image_arr=arr,
            affine_transform=tf,
            source_crs=crs_str,
            metadata=meta,
            image_name=os.path.basename(tiff_path)
        )

def run_inference_on_tiff(tiff_path: str, checkpoint_path: str = "outputs/checkpoints/best_model.pt") -> Dict[str, Any]:
    pipeline = SARIcebergInferencePipeline(checkpoint_path=checkpoint_path)
    return pipeline.predict_tiff(tiff_path)
