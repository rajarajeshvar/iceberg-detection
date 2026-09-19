import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.schemas import IcebergDetectionRequest, TrajectoryPredictionResponse
from app.services.trajectory_service import TrajectoryService
from app.segmentation.geospatial import parse_s1_filename

router = APIRouter(prefix="/api/v1/segmentation", tags=["SAR Iceberg Segmentation (SegFormer)"])

def get_segmentation_pipeline():
    from app.main import container
    return container.get("segmentation_pipeline")

def get_trajectory_service() -> TrajectoryService:
    from app.main import container
    return container["trajectory_service"]

class AnalyzeSampleRequest(BaseModel):
    filename: str = Field(..., description="Filename of GeoTIFF in S1 dataset")
    auto_predict_trajectories: bool = Field(True, description="Whether to automatically forecast drift trajectories for detected icebergs")

@router.get("/samples", summary="List available Sentinel-1 SAR sample scenes")
def list_sar_samples():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "S1UnetPlusPlus", "imgs")
    if not os.path.exists(base_dir):
        return {"samples": [], "total_available": 0}
        
    files = sorted([f for f in os.listdir(base_dir) if f.lower().endswith((".tif", ".tiff"))])
    samples = []
    for f in files[:50]:
        meta = parse_s1_filename(f)
        samples.append({
            "filename": f,
            "sensor": meta.get("sensor", "Sentinel-1"),
            "polarization": meta.get("polarization", "Dual-Pol"),
            "start_time": meta.get("start_time"),
            "resolution": meta.get("nominal_resolution_m", 40.0)
        })
    return {"samples": samples, "total_available": len(files)}

@router.post("/analyze-sample", summary="Run SegFormer segmentation & geospatial coordinate extraction on a SAR sample")
def analyze_sar_sample(
    req: AnalyzeSampleRequest,
    db: Session = Depends(get_db),
    pipeline = Depends(get_segmentation_pipeline),
    traj_service: TrajectoryService = Depends(get_trajectory_service)
):
    if pipeline is None:
        raise HTTPException(status_code=500, detail="Segmentation pipeline is not initialized.")
        
    safe_name = os.path.basename(req.filename)
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "S1UnetPlusPlus", "imgs")
    file_path = os.path.abspath(os.path.join(base_dir, safe_name))
    
    if not file_path.startswith(base_dir) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail=f"Sample file '{safe_name}' not found.")
        
    # Execute SegFormer inference
    res = pipeline.predict_tiff(file_path)
    
    # If no icebergs detected, guard against generating false metadata / trajectory
    if not res["has_detections"]:
        return {
            "status": "success",
            "message": "No iceberg targets detected in this SAR scene.",
            "total_detected": 0,
            "has_detections": False,
            "icebergs": [],
            "trajectories_generated": 0,
            "images": res["images"],
            "metadata": res["metadata"]
        }
        
    # Process detected icebergs: generate drift trajectories & register in DB
    enriched_icebergs = []
    trajectories_count = 0
    
    for ib in res["icebergs"]:
        ib_record = dict(ib)
        
        if req.auto_predict_trajectories:
            try:
                # Convert timestamp to ISO datetime
                try:
                    dt = datetime.fromisoformat(ib["timestamp"].replace("Z", "+00:00"))
                except Exception:
                    dt = datetime.utcnow()
                    
                det_req = IcebergDetectionRequest(
                    iceberg_id=ib["iceberg_id"],
                    latitude=ib["latitude"],
                    longitude=ib["longitude"],
                    timestamp=dt,
                    size_m=ib["size_m"],
                    confidence=ib["confidence"]
                )
                
                # Predict 6h-72h trajectory using ML drift model & oceanic APIs
                traj_res = traj_service.process_detection_and_predict(db, det_req)
                ib_record["trajectory_predictions"] = traj_res.predictions
                trajectories_count += 1
            except Exception as e:
                ib_record["trajectory_error"] = str(e)
                
        enriched_icebergs.append(ib_record)
        
    return {
        "status": "success",
        "message": f"Successfully segmented {len(enriched_icebergs)} iceberg target(s).",
        "total_detected": len(enriched_icebergs),
        "has_detections": True,
        "icebergs": enriched_icebergs,
        "trajectories_generated": trajectories_count,
        "images": res["images"],
        "metadata": res["metadata"]
    }

@router.post("/analyze-upload", summary="Upload custom SAR GeoTIFF for SegFormer segmentation & trajectory prediction")
async def analyze_sar_upload(
    file: UploadFile = File(...),
    auto_predict_trajectories: bool = Form(True),
    db: Session = Depends(get_db),
    pipeline = Depends(get_segmentation_pipeline),
    traj_service: TrajectoryService = Depends(get_trajectory_service)
):
    if pipeline is None:
        raise HTTPException(status_code=500, detail="Segmentation pipeline is not initialized.")
        
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = f"upload_{uuid.uuid4().hex}.tif"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    with open(temp_path, "wb") as f:
        f.write(contents)
        
    try:
        res = pipeline.predict_tiff(temp_path)
        
        if not res["has_detections"]:
            return {
                "status": "success",
                "message": "No iceberg targets detected in uploaded SAR image.",
                "total_detected": 0,
                "has_detections": False,
                "icebergs": [],
                "trajectories_generated": 0,
                "images": res["images"],
                "metadata": res["metadata"]
            }
            
        enriched_icebergs = []
        trajectories_count = 0
        for ib in res["icebergs"]:
            ib_record = dict(ib)
            if auto_predict_trajectories:
                try:
                    dt = datetime.utcnow()
                    det_req = IcebergDetectionRequest(
                        iceberg_id=ib["iceberg_id"],
                        latitude=ib["latitude"],
                        longitude=ib["longitude"],
                        timestamp=dt,
                        size_m=ib["size_m"],
                        confidence=ib["confidence"]
                    )
                    traj_res = traj_service.process_detection_and_predict(db, det_req)
                    ib_record["trajectory_predictions"] = traj_res.predictions
                    trajectories_count += 1
                except Exception as e:
                    ib_record["trajectory_error"] = str(e)
            enriched_icebergs.append(ib_record)
            
        return {
            "status": "success",
            "message": f"Successfully segmented {len(enriched_icebergs)} iceberg target(s) from upload.",
            "total_detected": len(enriched_icebergs),
            "has_detections": True,
            "icebergs": enriched_icebergs,
            "trajectories_generated": trajectories_count,
            "images": res["images"],
            "metadata": res["metadata"]
        }
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
