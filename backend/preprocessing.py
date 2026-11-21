"""
Preprocessing and Feature Engineering Module for Road Quality Monitor
Transforms raw multi-axis accelerometer and gyroscope readings into
distinguishable physical features for machine learning classification.
"""

import math
from typing import List, Dict, Any, Union
import numpy as np

# Gravity constant on Earth surface (m/s^2)
GRAVITY_NOMINAL = 9.80665

# Expected feature column names for the machine learning model
FEATURE_COLUMNS = [
    "accel_mag_mean",
    "accel_mag_max",
    "accel_mag_std",
    "accel_z_delta",
    "accel_jerk",
    "gyro_mag_mean"
]


def calculate_magnitude(x: float, y: float, z: float) -> float:
    """Calculate Euclidean 3D vector magnitude sqrt(x^2 + y^2 + z^2)."""
    return math.sqrt(float(x)**2 + float(y)**2 + float(z)**2)


def extract_features_from_window(readings: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extract statistical features from a time window of sensor samples.
    Each sample dict may contain:
      - x, y, z (accelerometer in m/s^2)
      - gx, gy, gz (gyroscope in rad/s, optional)
    """
    if not readings:
        # Default nominal resting state (normal smooth road)
        return {
            "accel_mag_mean": GRAVITY_NOMINAL,
            "accel_mag_max": GRAVITY_NOMINAL,
            "accel_mag_std": 0.05,
            "accel_z_delta": 0.05,
            "accel_jerk": 0.1,
            "gyro_mag_mean": 0.02
        }

    mags = []
    z_vals = []
    gyro_mags = []

    for r in readings:
        x = float(r.get("x", 0.0) or 0.0)
        y = float(r.get("y", 0.0) or 0.0)
        z = float(r.get("z", GRAVITY_NOMINAL) or GRAVITY_NOMINAL)

        mag = calculate_magnitude(x, y, z)
        mags.append(mag)
        z_vals.append(z)

        gx = float(r.get("gx", 0.0) or 0.0)
        gy = float(r.get("gy", 0.0) or 0.0)
        gz = float(r.get("gz", 0.0) or 0.0)
        gyro_mags.append(calculate_magnitude(gx, gy, gz))

    mags_arr = np.array(mags, dtype=np.float64)
    z_arr = np.array(z_vals, dtype=np.float64)
    gyro_arr = np.array(gyro_mags, dtype=np.float64)

    mag_mean = float(np.mean(mags_arr))
    mag_max = float(np.max(mags_arr))
    mag_std = float(np.std(mags_arr)) if len(mags_arr) > 1 else 0.1

    # Vertical delta from gravity
    z_deltas = np.abs(z_arr - GRAVITY_NOMINAL)
    z_delta_max = float(np.max(z_deltas))

    # Rate of change / jerk approximation
    if len(mags_arr) > 1:
        diffs = np.abs(np.diff(mags_arr))
        jerk_max = float(np.max(diffs))
    else:
        jerk_max = abs(mag_max - GRAVITY_NOMINAL)

    gyro_mean = float(np.mean(gyro_arr))

    return {
        "accel_mag_mean": round(mag_mean, 4),
        "accel_mag_max": round(mag_max, 4),
        "accel_mag_std": round(mag_std, 4),
        "accel_z_delta": round(z_delta_max, 4),
        "accel_jerk": round(jerk_max, 4),
        "gyro_mag_mean": round(gyro_mean, 4)
    }


def extract_features_from_single_event(data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract features from a single event payload.
    Supports either pre-aggregated features or raw single-point acceleration.
    """
    # If a full window of samples is provided
    if "readings" in data and isinstance(data["readings"], list) and len(data["readings"]) > 0:
        return extract_features_from_window(data["readings"])

    # If features are already explicitly provided
    if all(k in data for k in FEATURE_COLUMNS):
        return {k: float(data[k]) for k in FEATURE_COLUMNS}

    # Otherwise synthesize features from single accelerometer/gyroscope readings
    ax = float(data.get("accel_x", 0.0) or 0.0)
    ay = float(data.get("accel_y", 0.0) or 0.0)
    az = float(data.get("accel_z", GRAVITY_NOMINAL) or GRAVITY_NOMINAL)
    mag = calculate_magnitude(ax, ay, az)

    peak = float(data.get("peak_accel", mag) or mag)
    variance = float(data.get("accel_variance", abs(mag - GRAVITY_NOMINAL) * 0.4) or 0.2)
    gyro_mag = float(data.get("gyro_mag", 0.0) or 0.0)

    z_delta = abs(az - GRAVITY_NOMINAL)
    jerk = abs(peak - GRAVITY_NOMINAL)

    return {
        "accel_mag_mean": round(mag, 4),
        "accel_mag_max": round(peak, 4),
        "accel_mag_std": round(math.sqrt(max(0.001, variance)), 4),
        "accel_z_delta": round(z_delta, 4),
        "accel_jerk": round(jerk, 4),
        "gyro_mag_mean": round(gyro_mag, 4)
    }


def features_to_vector(features: Dict[str, float]) -> np.ndarray:
    """Convert features dictionary into a 2D numpy array row for model input."""
    row = [features.get(col, 0.0) for col in FEATURE_COLUMNS]
    return np.array([row], dtype=np.float64)
