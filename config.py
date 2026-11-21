"""
Configuration settings for the Road Quality Monitor application.
Supports environment variables with sensible local defaults.
"""

import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Data directory
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Cryptography keys directory
KEYS_DIR = DATA_DIR / "keys"
KEYS_DIR.mkdir(parents=True, exist_ok=True)

# Database configuration
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(DATA_DIR / "road_quality.db"))

# Secret and key paths
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-for-cse-project-2026")
FERNET_KEY_FILE = os.environ.get("FERNET_KEY_FILE", str(KEYS_DIR / "secret.key"))
RSA_PRIVATE_KEY_FILE = os.environ.get("RSA_PRIVATE_KEY_FILE", str(KEYS_DIR / "private_key.pem"))
RSA_PUBLIC_KEY_FILE = os.environ.get("RSA_PUBLIC_KEY_FILE", str(KEYS_DIR / "public_key.pem"))

# Machine Learning model directory & paths
ML_DIR = BASE_DIR / "ml"
MODEL_DIR = ML_DIR / "model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = os.environ.get("MODEL_PATH", str(MODEL_DIR / "road_classifier.joblib"))
SCALER_PATH = os.environ.get("SCALER_PATH", str(MODEL_DIR / "scaler.joblib"))
METADATA_PATH = os.environ.get("METADATA_PATH", str(MODEL_DIR / "model_metadata.json"))
SAMPLE_DATASET_PATH = os.environ.get("SAMPLE_DATASET_PATH", str(ML_DIR / "sample_sensor_data.csv"))

# Geospatial Clustering (DBSCAN) settings
# DBSCAN eps in kilometers (default 0.05 km = 50 meters)
# Earth radius in kilometers ~ 6371.0088 km
DBSCAN_EPS_KM = float(os.environ.get("DBSCAN_EPS_KM", 0.05))
DBSCAN_MIN_SAMPLES = int(os.environ.get("DBSCAN_MIN_SAMPLES", 2))
EARTH_RADIUS_KM = 6371.0088

# Class labels
LABEL_MAPPING = {
    0: "Normal Road",
    1: "Speed Breaker",
    2: "Pothole"
}

# Reverse mapping for training
REVERSE_LABEL_MAPPING = {
    "Normal Road": 0,
    "Speed Breaker": 1,
    "Pothole": 2
}

# Distress Index Priority Thresholds
# Score: 0 - 100
PDI_THRESHOLDS = {
    "Low": (0.0, 30.0),
    "Moderate": (30.0, 60.0),
    "High": (60.0, 80.0),
    "Critical": (80.0, 100.0)
}
