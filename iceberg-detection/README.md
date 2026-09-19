# CryoPulse AI — Autonomous Satellite Iceberg Detection & Drift Prediction Platform

An integrated end-to-end maritime safety platform for Antarctic & Arctic navigation, fusing **Satellite Synthetic Aperture Radar (SAR)**, **Coriolis Hydrodynamic Drift Physics**, **Machine Learning Trajectory Forecasting (+6h to +72h)**, and **A* Optimal Safe Routing**.

---

## Architecture Overview

```text
                                  ┌────────────────────────┐
                                  │ Sentinel-1 / RCM SAR   │
                                  │ Satellite Ingestion    │
                                  └───────────┬────────────┘
                                              │
                                              ▼
┌────────────────────────┐         ┌────────────────────────┐
│ React Frontend         │ ◄─────► │ FastAPI Backend        │
│ (Vite @ :5173)         │         │ (Python @ :8000)       │
├────────────────────────┤         ├────────────────────────┤
│ • GhostFibers Shader   │         │ • Trajectory Engine    │
│ • 3D Antarctic Globe   │         │ • Environmental Drag   │
│ • ARPA Tactical Radar  │         │ • Uncertainty Radii    │
│ • Operations Console   │         │ • A* Avoidance Routing │
└────────────────────────┘         └────────────────────────┘
```

---

## Directory Structure

```
iceberg-detection/
├── frontend/                     # Modern React + Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── GhostFibers.jsx   # React Bits WebGL2 animated background
│   │   │   ├── SpecularButton.jsx# React Bits mouse-tracking specular buttons
│   │   │   ├── BorderGlow.jsx    # React Bits edge-sensing reactive cards
│   │   │   ├── GlobeView.jsx     # 3D interactive Antarctic Globe (react-globe.gl)
│   │   │   ├── TacticalRadar.jsx # ARPA Tactical Radar HUD (360° azimuth dial)
│   │   │   └── DetailModal.jsx   # Live route & REST contract decision viewer
│   │   ├── pages/
│   │   │   ├── LandingPage.jsx   # Public mission overview & features
│   │   │   └── OperationsConsole.jsx # Dedicated maritime navigation workstation
│   │   └── services/api.js       # Live connectors to FastAPI backend
│   └── package.json
│
└── prediction-engine/            # Python FastAPI Trajectory & Decision Engine
    ├── app/
    │   ├── api/                  # REST endpoints (/prediction, /route, /health)
    │   ├── ml/                   # XGBoost trajectory models & training
    │   ├── routing/              # A* safe navigation & fuel score optimizer
    │   ├── services/             # Environmental, trajectory & uncertainty services
    │   └── main.py               # Application entry point & CORS
    ├── run.py                    # Uvicorn server runner
    └── requirements.txt
```

---

## Quickstart Guide

### 1. Run Backend Engine (FastAPI)
```bash
cd prediction-engine

# Activate virtual environment or use Python
python run.py --port 8000
```
- API is live at: `http://127.0.0.1:8000`
- Interactive Swagger API Docs: `http://127.0.0.1:8000/docs`

### 2. Run Frontend Application (React + Vite)
```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
- Web Application is live at: `http://127.0.0.1:5173`

---

## Key Capabilities

- **3D Antarctic Globe View (`react-globe.gl`)**: Real-time 3D Earth tracking of detected iceberg bodies, drift vectors, and vessel routing corridors.
- **ARPA Tactical Radar HUD**: High-fidelity maritime radar with 360° azimuth dial, realistic phosphor sweep, range scales (3–24 NM), and collision risk warnings.
- **Coriolis & Hydrodynamic Modeling**: Accounts for wind leeway deflection, Ekman current drift, water-line ablation, and sea-ice concentration pack resistance.
- **A* Safe Fuel Routing**: Generates collision-avoidance waypoints balancing safety distance vs fuel consumption penalties.
- **React Bits Visual Suite**: Integrated `<GhostFibers />`, `<SpecularButton />`, and `<BorderGlow />`.
