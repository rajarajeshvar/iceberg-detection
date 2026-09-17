import pytest
from app.services.uncertainty_service import UncertaintyService
from app.ml.feature_engineering import extract_features
from app.ml.model import IcebergTrajectoryModel


def test_uncertainty_growth_and_confidence_decay():
    # 6h horizon
    conf_6h, rad_6h = UncertaintyService.calculate_uncertainty(6, detection_confidence=0.94)
    # 72h horizon
    conf_72h, rad_72h = UncertaintyService.calculate_uncertainty(72, detection_confidence=0.94)

    assert conf_6h > conf_72h
    assert rad_6h < rad_72h
    assert rad_6h > 0.0
    assert rad_72h > 15.0


def test_feature_engineering_extraction():
    feats = extract_features(
        latitude=-64.231,
        longitude=42.512,
        current_speed=0.5,
        current_direction=45.0,
        wind_speed=12.0,
        wind_direction=60.0,
        temperature=-1.5,
        sea_ice_concentration=0.7,
        size_m=145.0
    )

    assert "net_speed_kmh" in feats
    assert "net_direction_deg" in feats
    assert "ice_damping" in feats
    assert 0.0 <= feats["ice_damping"] <= 1.0


def test_trajectory_model_fallback_prediction():
    model = IcebergTrajectoryModel(model_path=None)  # Kinematic fallback
    feats = extract_features(-64.0, 40.0, 0.5, 45.0, 10.0, 60.0, -1.0, 0.5)

    preds = model.predict_trajectory(feats, horizons=[6, 12, 24, 48, 72])

    assert len(preds) == 5
    assert preds[0]["hours_ahead"] == 6
    assert preds[-1]["hours_ahead"] == 72

    # Positions should change progressively
    assert preds[0]["latitude"] != preds[-1]["latitude"]
    assert preds[0]["longitude"] != preds[-1]["longitude"]
