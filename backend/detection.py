"""
Detection Pipeline Coordinator
Orchestrates raw sensor ingestion -> feature engineering -> Random Forest inference
-> PDI prioritization -> cryptographic sealing (Fernet, SHA-256, RSA) -> persistence.
"""

import datetime
from typing import Dict, Any

from backend import preprocessing, severity, database, clustering
from ml import predict


def process_sensor_event(payload: Dict[str, Any], trigger_clustering: bool = True) -> Dict[str, Any]:
    """
    Execute full pipeline for incoming sensor reading:
    1. Extract features (acceleration magnitude, jerk, variance, gyro).
    2. Random Forest prediction (Normal Road, Speed Breaker, Pothole).
    3. Compute PDI score (0 - 100) & priority level.
    4. Store in database with Fernet encryption, SHA-256 hash, and RSA digital signature.
    5. Optionally recalculate spatial clusters.
    """
    # 1. Feature extraction
    features = preprocessing.extract_features_from_single_event(payload)

    # 2. Machine Learning inference
    ml_result = predict.predict_road_event(features)
    predicted_type = ml_result["event_type"]
    confidence = ml_result["confidence"]

    # 3. Pavement Distress Index
    pdi_score, priority = severity.calculate_single_pdi(
        event_type=predicted_type,
        confidence=confidence,
        peak_accel=features.get("accel_mag_max", 9.8),
        accel_jerk=features.get("accel_jerk", 0.0)
    )

    # 4. Construct complete record
    device_id = str(payload.get("device_id") or "DEV-SIM-001")
    timestamp = str(payload.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).isoformat())
    lat = float(payload.get("latitude") or 12.9716)
    lon = float(payload.get("longitude") or 77.5946)
    is_simulated = bool(payload.get("is_simulated", False))

    record_to_insert = {
        "device_id": device_id,
        "timestamp": timestamp,
        "latitude": lat,
        "longitude": lon,
        "accel_x": float(payload.get("accel_x", 0.0) or 0.0),
        "accel_y": float(payload.get("accel_y", 0.0) or 0.0),
        "accel_z": float(payload.get("accel_z", 9.8) or 9.8),
        "accel_mag": features["accel_mag_mean"],
        "peak_accel": features["accel_mag_max"],
        "accel_variance": features["accel_mag_std"] ** 2,
        "gyro_mag": features["gyro_mag_mean"],
        "event_type": predicted_type,
        "confidence": confidence,
        "pdi_score": pdi_score,
        "priority_level": priority,
        "is_simulated": is_simulated
    }

    # Insert into database (this handles Fernet encryption, SHA-256 hashing, and RSA signing)
    detection_id = database.insert_detection(record_to_insert)

    # 5. Spatial clustering update
    if trigger_clustering:
        clustering.recalculate_and_save_clusters()

    # Retrieve saved record with cryptographic proof
    saved_record = database.get_detection_by_id(detection_id)

    return {
        "success": True,
        "detection_id": detection_id,
        "event_type": predicted_type,
        "confidence": confidence,
        "probabilities": ml_result["probabilities"],
        "pdi_score": pdi_score,
        "priority_level": priority,
        "features": features,
        "cryptography": {
            "data_hash": saved_record.get("data_hash"),
            "digital_signature_preview": saved_record.get("digital_signature", "")[:32] + "...",
            "encrypted_latitude_preview": saved_record.get("encrypted_latitude", "")[:24] + "...",
            "encrypted_longitude_preview": saved_record.get("encrypted_longitude", "")[:24] + "..."
        },
        "record": saved_record
    }
