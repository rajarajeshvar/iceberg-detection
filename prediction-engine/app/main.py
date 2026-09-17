import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from dotenv import load_dotenv

load_dotenv()

from app.database.database import init_db
from app.ml.model import IcebergTrajectoryModel
from app.ml.train import train_and_save_model
from app.services.environmental_service import EnvironmentalService
from app.services.trajectory_service import TrajectoryService
from app.services.prediction_service import PredictionService
from app.api.routes_health import router as health_router
from app.api.routes_prediction import router as prediction_router
from app.api.routes_route import router as route_router
from app.api.routes_feature4 import router as feature4_router

# Service dependency container
container = {}

# Initialize Database tables on import
init_db()

model_path = os.getenv("MODEL_PATH", "./models/iceberg_trajectory_model.joblib")
if not os.path.exists(model_path):
    print(f"No existing model found at {model_path}. Training baseline ML model...")
    try:
        train_and_save_model(model_path)
    except Exception as e:
        print(f"[Warning] Automatic model training failed on startup: {e}")

# Load ML Model & Services on module import
model = IcebergTrajectoryModel(model_path)
use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")
env_service = EnvironmentalService(use_mock=use_mock)

container["model"] = model
container["env_service"] = env_service
container["trajectory_service"] = TrajectoryService(model, env_service)
container["prediction_service"] = PredictionService(env_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Antarctic Navigation AI Decision Support System initialized successfully.")
    yield
    print("Shutting down Antarctic Navigation System.")


app = FastAPI(
    title=os.getenv("APP_NAME", "Antarctic Iceberg Navigation Decision Support System"),
    description=(
        "Production-ready FastAPI backend for SIH26059 Antarctic navigation decision support system. "
        "Provides satellite iceberg detection ingestion (Feature 1), 6h-72h trajectory predictions (Feature 2), "
        "multi-route optimization with Safety/Fuel rankings & dynamic re-routing (Feature 3), and "
        "AI navigation decision support, real-time WebSocket alerts, explainable recommendations & What-If simulation (Feature 4)."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(prediction_router)
app.include_router(route_router)
app.include_router(feature4_router)


# Serve Web Dashboard HTML at GET /
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_dashboard():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(template_path):
        return FileResponse(template_path)
    return HTMLResponse("<h2>Antarctic Navigation System Backend is running. Access API docs at <a href='/docs'>/docs</a></h2>")
