"""
Prediction Module for Road Quality Monitor
Loads the trained Random Forest classifier and scaler to predict road anomaly types.
"""

from pathlib import Path
from typing import Dict, Any
import numpy as np
import joblib

import config
from backend.preprocessing import FEATURE_COLUMNS, features_to_vector

# Cache model and scaler in memory
_MODEL = None
_SCALER = None


def load_model_and_scaler():
    """Load model and scaler from disk. Train on the fly if missing."""
    global _MODEL, _SCALER
    model_path = Path(config.MODEL_PATH)
    scaler_path = Path(config.SCALER_PATH)

    if not model_path.exists() or not scaler_path.exists():
        from ml.train_model import train
        train()

    if _MODEL is None:
        _MODEL = joblib.load(config.MODEL_PATH)
    if _SCALER is None:
        _SCALER = joblib.load(config.SCALER_PATH)

    return _MODEL, _SCALER


def predict_road_event(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Predict road anomaly class and confidence from extracted features.
    
    Returns:
    {
        "class_id": int,
        "event_type": str,
        "confidence": float,
        "probabilities": dict,
        "features": dict
    }
    """
    model, scaler = load_model_and_scaler()

    # Create 2D feature array and scale
    X_raw = features_to_vector(features)
    X_scaled = scaler.transform(X_raw)

    # Predict class & class probabilities
    pred_class_id = int(model.predict(X_scaled)[0])
    probabilities = model.predict_proba(X_scaled)[0]

    confidence = float(np.max(probabilities))
    event_type = config.LABEL_MAPPING.get(pred_class_id, "Unknown")

    prob_dict = {
        config.LABEL_MAPPING.get(i, f"Class {i}"): round(float(prob), 4)
        for i, prob in enumerate(probabilities)
    }

    return {
        "class_id": pred_class_id,
        "event_type": event_type,
        "confidence": round(confidence, 4),
        "probabilities": prob_dict,
        "features": {col: round(float(features.get(col, 0.0)), 4) for col in FEATURE_COLUMNS}
    }
