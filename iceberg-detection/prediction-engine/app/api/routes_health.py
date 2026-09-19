import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.database import get_db
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    System health check endpoint verifying application state, DB connection, and ML model status.
    """
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    # Check model file presence
    model_path = os.getenv("MODEL_PATH", "./models/iceberg_trajectory_model.joblib")
    model_loaded = os.path.exists(model_path)

    use_mock = os.getenv("USE_MOCK_DATA", "true").lower() in ("true", "1", "yes")

    return HealthResponse(
        status="healthy" if db_connected else "degraded",
        app_name=os.getenv("APP_NAME", "Antarctic Iceberg Trajectory & Sea-Ice Prediction Engine"),
        environment=os.getenv("APP_ENV", "development"),
        mock_data_enabled=use_mock,
        database_connected=db_connected,
        model_loaded=model_loaded,
        model_version="xgboost-physics-v1" if model_loaded else "physics-kinematic-baseline"
    )
