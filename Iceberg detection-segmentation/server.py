import os
import sys
import io
import uuid
import base64
import json
import numpy as np
import cv2
import rasterio
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any

# Ensure project root is in sys.path regardless of execution CWD
from path_utils import PROJECT_ROOT, resolve_path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from inference.predict import SARIcebergInferencePipeline
from geospatial.metadata import parse_s1_filename

app = FastAPI(title="Sentinel-1 SAR Iceberg Detection & Segmentation API")

# Secure CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Maximum allowed upload size (50 MB)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".tif", ".tiff"}

# Global Pipeline Holder (initialized lazily or on startup)
pipeline: Optional[SARIcebergInferencePipeline] = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        ckpt = resolve_path("outputs/checkpoints/best_model.pt")
        if not os.path.exists(ckpt):
            ckpt = resolve_path("outputs/checkpoints/latest_model.pt")
        pipeline = SARIcebergInferencePipeline(checkpoint_path=ckpt)
    return pipeline

def encode_img_base64(img_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", img_bgr)
    return base64.b64encode(buf).decode("utf-8")

def encode_gray_base64(gray: np.ndarray) -> str:
    # Scale float or int mask to uint8 [0, 255]
    gray_arr = gray.copy()
    if np.issubdtype(gray_arr.dtype, np.floating):
        gray_uint8 = (np.clip(gray_arr, 0.0, 1.0) * 255).astype(np.uint8)
    else:
        gray_uint8 = ((gray_arr > 0).astype(np.uint8) * 255) if gray_arr.max() <= 1 else gray_arr.astype(np.uint8)
    _, buf = cv2.imencode(".png", gray_uint8)
    return base64.b64encode(buf).decode("utf-8")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "S1-Iceberg-SegFormer"}

@app.get("/api/samples")
def get_sample_list():
    imgs_dir = resolve_path("S1UnetPlusPlus/imgs")
    if not os.path.exists(imgs_dir):
        return {"samples": []}
    files = sorted([f for f in os.listdir(imgs_dir) if f.lower().endswith((".tif", ".tiff"))])
    samples = []
    for f in files[:40]:  # First 40 representative samples
        meta = parse_s1_filename(f)
        samples.append({
            "filename": f,
            "sensor": meta.get("sensor", "Sentinel-1"),
            "start_time": meta.get("start_time"),
            "polarization": meta.get("polarization")
        })
    return {"samples": samples, "total_available": len(files)}

@app.get("/api/metrics")
def get_model_metrics():
    metrics_path = resolve_path("outputs/checkpoints/test_metrics.json")
    history_path = resolve_path("outputs/checkpoints/training_history.json")
    
    metrics = {}
    history = []
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
            
    return {"test_metrics": metrics, "training_history": history}

class SamplePredictRequest(BaseModel):
    filename: str

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        safe_name = os.path.basename(v)
        if not safe_name or safe_name != v:
            raise ValueError("Invalid filename: Path traversal characters are not permitted.")
        _, ext = os.path.splitext(safe_name)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid file extension. Allowed extensions: {ALLOWED_EXTENSIONS}")
        return safe_name

@app.post("/api/predict-sample")
def predict_sample(req: SamplePredictRequest):
    p = get_pipeline()
    
    # Strictly resolve within imgs directory
    base_dir = resolve_path("S1UnetPlusPlus/imgs")
    tiff_path = os.path.abspath(os.path.join(base_dir, req.filename))
    
    # Path traversal safeguard
    if not tiff_path.startswith(base_dir) or not os.path.isfile(tiff_path):
        raise HTTPException(status_code=404, detail="Sample TIFF not found")
        
    res = p.predict_tiff(tiff_path)
    
    # Base SAR view
    with rasterio.open(tiff_path) as src:
        arr = np.nan_to_num(src.read(), nan=0.0)
    sar_preview = (np.clip(arr[0], 0, 1) * 255).astype(np.uint8)
    
    # Masks and visual maps
    prob_b64 = encode_gray_base64(res["probability_map"])
    mask_b64 = encode_gray_base64(res["binary_mask"])
    sar_b64 = encode_gray_base64(sar_preview)
    overlay_b64 = encode_img_base64(res["overlay_bgr"])
    
    # Ground truth if available
    stem = os.path.splitext(req.filename)[0]
    gt_mask_path = resolve_path(os.path.join("S1UnetPlusPlus/masks", f"{stem}_mask.tif"))
    gt_b64 = None
    if os.path.exists(gt_mask_path):
        with rasterio.open(gt_mask_path) as src_gt:
            gt_arr = src_gt.read(1)
            gt_b64 = encode_gray_base64(gt_arr)
            
    return {
        "image_name": req.filename,
        "total_detected": res["total_detected"],
        "iceberg_states": res["iceberg_states_document"]["iceberg_states"],
        "document": res["iceberg_states_document"],
        "images": {
            "sar": sar_b64,
            "probability_map": prob_b64,
            "predicted_mask": mask_b64,
            "ground_truth_mask": gt_b64,
            "overlay": overlay_b64
        }
    }

@app.post("/api/predict-upload")
async def predict_upload(file: UploadFile = File(...)):
    # Validate filename and extension
    original_filename = os.path.basename(file.filename or "uploaded.tif")
    _, ext = os.path.splitext(original_filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type '{ext}'. Allowed types: {ALLOWED_EXTENSIONS}")

    p = get_pipeline()
    contents = await file.read()
    
    # Enforce file size limit
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save to a unique temporary file to prevent collision and path traversal
    temp_dir = resolve_path("outputs/temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"upload_{uuid.uuid4().hex}{ext.lower()}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    with open(temp_path, "wb") as fp:
        fp.write(contents)
        
    try:
        res = p.predict_tiff(temp_path)
        
        with rasterio.open(temp_path) as src:
            arr = np.nan_to_num(src.read(), nan=0.0)
        sar_preview = (np.clip(arr[0], 0, 1) * 255).astype(np.uint8)
        
        prob_b64 = encode_gray_base64(res["probability_map"])
        mask_b64 = encode_gray_base64(res["binary_mask"])
        sar_b64 = encode_gray_base64(sar_preview)
        overlay_b64 = encode_img_base64(res["overlay_bgr"])
        
        return {
            "image_name": original_filename,
            "total_detected": res["total_detected"],
            "iceberg_states": res["iceberg_states_document"]["iceberg_states"],
            "document": res["iceberg_states_document"],
            "images": {
                "sar": sar_b64,
                "probability_map": prob_b64,
                "predicted_mask": mask_b64,
                "ground_truth_mask": None,
                "overlay": overlay_b64
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process TIFF file: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

# Serve Frontend static assets
frontend_dir = resolve_path("frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Sentinel-1 SAR Iceberg Segmentation Module</h1><p>Frontend file not found.</p>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
