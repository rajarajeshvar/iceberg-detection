# Sentinel-1 SAR Iceberg Detection & Semantic Segmentation (SegFormer-B0)

An end-to-end, scientific-grade PyTorch and Hugging Face Transformers module for automated iceberg detection, binary semantic segmentation, and geospatial `IcebergState` extraction from Sentinel-1 SAR imagery.

---

## 🛰️ System Overview & Capabilities

This module provides the detection foundation for maritime navigation safety and iceberg drift tracking in polar and sub-polar waters:

```text
Sentinel-1 SAR GeoTIFF (.tif)
              ↓
Quality Control & Radiometric Preprocessing
              ↓
SegFormer-B0 Hierarchical Transformer Model
              ↓
Probability Heatmap & Binary Segmentation Mask
              ↓
Morphological Cleanup & Contour Extraction
              ↓
Individual Iceberg Object Detection (IB_0001, IB_0002, ...)
              ↓
Metric Geometry & Physical Feature Extraction (Area, Perimeter, Length, Width)
              ↓
Geospatial Coordinate Transform (EPSG:3996 → EPSG:4326 Lat/Lon)
              ↓
Machine-Readable IcebergState Document (JSON)
              ↓
Interactive Web Visualization & FastAPI Endpoint
```

---

## 📊 Dataset & Sensor Characteristics

* **Sensor Modality**: Sentinel-1A / Sentinel-1B C-band Synthetic Aperture Radar (SAR).
* **Product Level**: Level-1 Ground Range Detected Medium Resolution (`GRDM_1SDH`), Extra Wide Swath (`EW`).
* **Polarizations**: Dual-Polarization ($\text{HH} + \text{HV}$).
* **Spatial Resolution**: $40.0\,\text{m} \times 40.0\,\text{m}$ per pixel ($1\,\text{pixel} = 1600\,\text{m}^2$).
* **Coordinate Reference System**: `EPSG:3996` (WGS 84 / IBCAO Polar Stereographic North).
* **Dataset Splits**:
  * **Train**: 310 image-mask pairs ($288,319$ iceberg pixels, $1.42\%$ foreground density).
  * **Validation**: 38 image-mask pairs ($30,282$ iceberg pixels).
  * **Test**: 35 image-mask pairs ($35,014$ iceberg pixels).

---

## 🧠 SegFormer-B0 Architecture & Loss

* **Encoder**: `nvidia/mit-b0` hierarchical Mix Transformer with multi-level receptive fields ($1/4, 1/8, 1/16, 1/32$).
* **Decoder**: Lightweight All-MLP decoder aggregating multi-scale features to $256 \times 256$.
* **Classification**: Binary semantic segmentation (`num_classes = 2`).
* **Loss Function**: Weighted combination of Focal/Cross-Entropy Loss ($\alpha=0.5$) and Soft Dice Loss ($\beta=0.5$) with positive class weighting ($10\times$) to overcome severe class imbalance.

---

## 🧊 IcebergState Object Schema

Every detected iceberg object is converted into a standardized, machine-readable JSON structure:

```json
{
  "iceberg_id": "IB_0001",
  "source_image": "S1A_EW_GRDM_1SDH_20160607T191602_...",
  "metadata_available": true,
  "timestamp": "2016-06-07T19:16:02Z",
  "latitude": 68.5831,
  "longitude": -32.5120,
  "projected_x": -1279357.11,
  "projected_y": -2004543.73,
  "crs": "EPSG:3996",
  "area_pixels": 420,
  "area_m2": 672000.0,
  "area_km2": 0.672,
  "perimeter_pixels": 88.4,
  "perimeter_m": 3536.0,
  "length_m": 1240.0,
  "width_m": 620.0,
  "orientation_deg": 42.5,
  "bounding_box": {
    "x_min": 110,
    "y_min": 80,
    "x_max": 145,
    "y_max": 110
  },
  "centroid_pixel": {
    "x": 128.5,
    "y": 94.2
  },
  "segmentation_confidence": 0.941,
  "sensor": "Sentinel-1A",
  "mode": "EW",
  "polarization": "HH+HV"
}
```

---

## 📁 Repository Structure

```text
├── data/
│   ├── raw/                 <- Untouched source data
│   └── processed/           <- QC-verified training/validation/test tensors
├── preprocessing/
│   ├── inspect_dataset.py   <- Full dataset audit & pairing verification
│   ├── inspect_tiff.py      <- Single GeoTIFF inspection tool
│   ├── quality_control.py   <- Radiometric normalization & NaN handling
│   └── prepare_dataset.py   <- Build clean training tensors
├── models/
│   └── segformer.py         <- SegFormer-B0 PyTorch architecture
├── training/
│   ├── dataset.py           <- PyTorch Dataset with SAR-safe augmentations
│   ├── losses.py            <- Combined Cross-Entropy + Dice Loss
│   ├── evaluate.py          <- IoU, Dice/F1, Precision, Recall, Latency
│   └── train.py             <- Reproducible training & checkpointing loop
├── geospatial/
│   ├── metadata.py          <- Sentinel-1 acquisition metadata parser
│   ├── coordinates.py       <- EPSG:3996 to WGS84 EPSG:4326 transform
│   └── measurements.py      <- Metric physical area/perimeter/dimensions
├── inference/
│   ├── predict.py           <- End-to-end inference pipeline
│   ├── extract_icebergs.py  <- Morphological & contour iceberg extractor
│   ├── state_object.py      <- IcebergState schema builder
│   └── evaluate_all_test.py <- Test set evaluation & visual exporter
├── outputs/
│   ├── checkpoints/         <- Saved model weights (best_model.pt)
│   ├── predictions/         <- Exported binary mask PNGs
│   ├── overlays/            <- Visual comparison grids
│   └── iceberg_states/      <- Exported IcebergState JSON documents
├── frontend/
│   ├── index.html           <- Responsive visualization interface
│   ├── style.css            <- Dark theme UI styling
│   └── app.js               <- Frontend application logic
├── server.py                <- FastAPI inference & visualization server
├── config.yaml              <- Pipeline parameters & hyperparameters
├── requirements.txt         <- Python dependencies
└── README.md
```

---

## 🚀 Quickstart & Usage

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Dataset Audit & Preprocessing
```bash
python preprocessing/inspect_dataset.py
python preprocessing/prepare_dataset.py
```

### 3. Model Training
```bash
python training/train.py
```

### 4. Batch Test Set Evaluation & Export
```bash
python inference/evaluate_all_test.py
```

### 5. Launch Visualization Server
```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000` in your web browser to interactively test sample scenes, upload new GeoTIFFs, and inspect extracted iceberg states.
