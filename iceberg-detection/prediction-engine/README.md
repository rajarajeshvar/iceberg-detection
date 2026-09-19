# SIH26059 Feature 2: Iceberg Trajectory & Sea-Ice Prediction Engine

A production-ready **Python FastAPI backend** that predicts the future movement of detected Antarctic icebergs (+6h, +12h, +24h, +48h, +72h) and provides sea-ice forecasting for maritime navigation decision support.

---

## 1. What Feature 2 Does

Feature 2 acts as the core predictive trajectory & environmental engine for the Antarctic navigation system:
- Receives detected iceberg positions and metadata from **Feature 1 (Satellite / Iceberg Detection Engine)**.
- Combines current positions with ocean currents, wind vectors (Coriolis leeway deflection), sea surface temperature, sea-ice concentration, and physical drag models.
- Predicts future (latitude, longitude) coordinates across multiple horizons (+6h, +12h, +24h, +48h, +72h).
- Calculates time-decaying prediction confidence and expanding uncertainty radii (km) for each horizon.
- Provides sea-ice concentration forecasting for maritime route planning.
- Serves standardized REST JSON contracts directly consumable by **Feature 3 (Risk & Routing Engine)** for CPA/TCPA collision risk calculation.

---

## 2. Architecture

```text
Feature 1 (Detection) ─────────► [ POST /api/v1/prediction/trajectory ]
                                                 │
                                                 ▼
                                        FastAPI Engine (app/main.py)
                                                 │
                        ┌────────────────────────┼────────────────────────┐
                        ▼                        ▼                        ▼
               EnvironmentalService     IcebergTrajectoryModel    UncertaintyService
               (Ocean/Wind/Ice)         (XGBoost + Physics)       (Confidence & Radius)
                        │                        │                        │
                        └────────────────────────┼────────────────────────┘
                                                 │
                                                 ▼
                                        SQLite DB (SQLAlchemy)
                                                 │
                                                 ▼
Feature 3 (Risk Engine) ◄─────── [ JSON Response (+6h to +72h) ]
```

---

## 3. Installation

### Requirements
- Python 3.9+
- Virtual environment (recommended)

```bash
cd prediction-engine

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Running the Backend

```bash
# Run the FastAPI Uvicorn server (auto-trains baseline model if not present)
python run.py

# Server will be accessible at:
# API Base URL: http://localhost:8000
# Interactive Swagger Docs: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

---

## 5. API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Backend status, DB connection, model status |
| `POST` | `/api/v1/prediction/trajectory` | Submit iceberg detection & compute trajectory |
| `GET` | `/api/v1/prediction/trajectory/{iceberg_id}` | Fetch latest trajectory predictions for an iceberg |
| `POST` | `/api/v1/prediction/sea-ice` | Forecast sea-ice concentration (+6h to +72h) |
| `GET` | `/api/v1/prediction/icebergs` | List all tracked icebergs |
| `GET` | `/docs` | OpenAPI / Swagger interactive documentation |

---

## 6. Input / Output Examples

### Trajectory Prediction Request (`POST /api/v1/prediction/trajectory`)

```json
{
  "iceberg_id": "IB001",
  "latitude": -64.231,
  "longitude": 42.512,
  "timestamp": "2026-09-14T10:00:00Z",
  "size_m": 145,
  "confidence": 0.94
}
```

### Trajectory Prediction Response

```json
{
  "iceberg_id": "IB001",
  "prediction_generated_at": "2026-09-14T10:00:00Z",
  "model_version": "xgboost-physics-v1",
  "predictions": [
    {
      "hours_ahead": 6,
      "latitude": -64.21,
      "longitude": 42.61,
      "confidence": 0.94,
      "uncertainty_radius_km": 2.1
    },
    {
      "hours_ahead": 12,
      "latitude": -64.18,
      "longitude": 42.74,
      "confidence": 0.90,
      "uncertainty_radius_km": 3.8
    },
    {
      "hours_ahead": 24,
      "latitude": -64.11,
      "longitude": 42.98,
      "confidence": 0.82,
      "uncertainty_radius_km": 7.4
    },
    {
      "hours_ahead": 48,
      "latitude": -64.02,
      "longitude": 43.31,
      "confidence": 0.70,
      "uncertainty_radius_km": 14.2
    },
    {
      "hours_ahead": 72,
      "latitude": -63.91,
      "longitude": 43.65,
      "confidence": 0.58,
      "uncertainty_radius_km": 22.5
    }
  ]
}
```

---

## 7. Mock Data Mode

The environment variable `USE_MOCK_DATA=true` enables synthetic data generation for environmental parameters and initial drift trajectories.

```bash
# In .env file:
USE_MOCK_DATA=true
```

When enabled, the service synthesizes realistic ocean currents (0.3–0.7 m/s), wind vectors, sea surface temperatures, and sea-ice concentration for any requested location in the Antarctic region.

---

## 8. ML Training

To explicitly re-train the trajectory prediction model on synthetic physics trajectories:

```bash
python run.py --train
# or
python -m app.ml.train
```

The trained model artifact will be serialized to `models/iceberg_trajectory_model.joblib`.

---

## 9. How Feature 1 Connects

Feature 1 (Satellite Detection Engine) connects directly via HTTP POST:

```text
Feature 1 (SAR/Optical Detection) ──► HTTP POST /api/v1/prediction/trajectory ──► Feature 2 Engine
```

Feature 1 does NOT need to run or know about the trajectory prediction model; it only provides the standardized JSON payload containing `iceberg_id`, `latitude`, `longitude`, `timestamp`, `size_m`, and `confidence`.

---

## 10. How Feature 3 Consumes Output

Feature 3 (Risk & Routing Engine) consumes the predictions array:

```text
Vessel Navigation Route
          ↓
Predicted Iceberg Position (lat, lon, time)
          ↓
Distance & CPA / TCPA (Closest Point of Approach / Time to CPA)
          ↓
Collision Risk Rating & Route Recalculation
```

---

## 11. Real Data Support vs Demo / Synthetic Data

> [!IMPORTANT]
> **DEMO / SYNTHETIC DATA CURRENTLY LOADED**
> The dataset in `data/sample/sample_trajectories.csv` and the training generator in `app/ml/train.py` use **synthetic demo data** designed to test and validate software pipelines. They do NOT represent scientifically validated historical Antarctic tracking data.

> [!NOTE]
> **REAL DATA SUPPORT READY**
> The backend architecture is modularly designed so real Antarctic datasets (e.g. US National Ice Center IBTrACS, Copernicus CMEMS ocean currents, ERA5 weather reanalysis) can be inserted by extending `EnvironmentalService` without altering any REST API or DB schemas.

---

## 12. Limitations of the Prototype

- **Data Source**: Current environmental parameters use deterministic trigonometric spatial-temporal synthesis instead of live atmospheric API connections.
- **Iceberg Geometry**: Icebergs are modeled as point masses with effective diameter drag (`size_m`) rather than 3D underwater keel shapes.
- **Wave / Bathymetry**: Shallow bathymetric grounding (grounded icebergs) and wave radiation stress are not yet incorporated.

---

## 13. Running Tests

Execute the complete pytest test suite:

```bash
pytest -v
```
