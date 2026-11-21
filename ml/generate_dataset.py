"""
Dataset Generator for Machine Learning Model
Generates synthetic sensor data representing:
- Normal Road (Class 0)
- Speed Breaker (Class 1)
- Pothole (Class 2)

NOTE: This dataset contains SYNTHETIC accelerometer and gyroscope features
engineered based on physical kinematics of road anomalies. It is designed for
academic demonstration and CSE coursework prototype evaluation.
"""

import csv
import random
from pathlib import Path

# Fix seed for reproducible scientific evaluation
random.seed(42)

DATASET_PATH = Path(__file__).resolve().parent / "sample_sensor_data.csv"


def generate_synthetic_dataset(num_samples_per_class: int = 150):
    rows = []

    # 1. Normal Road (smooth asphalt, small micro-vibrations)
    for _ in range(num_samples_per_class):
        mag_mean = round(random.gauss(9.81, 0.15), 4)
        mag_max = round(mag_mean + abs(random.gauss(0.3, 0.15)), 4)
        mag_std = round(abs(random.gauss(0.25, 0.1)), 4)
        z_delta = round(abs(random.gauss(0.3, 0.15)), 4)
        jerk = round(abs(random.gauss(0.4, 0.2)), 4)
        gyro = round(abs(random.gauss(0.08, 0.04)), 4)
        rows.append({
            "accel_mag_mean": mag_mean,
            "accel_mag_max": mag_max,
            "accel_mag_std": mag_std,
            "accel_z_delta": z_delta,
            "accel_jerk": jerk,
            "gyro_mag_mean": gyro,
            "label": "Normal Road",
            "class_id": 0,
            "data_source": "synthetic"
        })

    # 2. Speed Breaker (smooth undulating rise and fall, moderate pitch rotation)
    for _ in range(num_samples_per_class):
        mag_mean = round(random.gauss(11.2, 0.6), 4)
        mag_max = round(random.gauss(13.8, 0.9), 4)
        mag_std = round(abs(random.gauss(1.9, 0.4)), 4)
        z_delta = round(abs(random.gauss(3.8, 0.8)), 4)
        jerk = round(abs(random.gauss(2.8, 0.6)), 4)
        gyro = round(abs(random.gauss(1.1, 0.3)), 4)
        rows.append({
            "accel_mag_mean": mag_mean,
            "accel_mag_max": mag_max,
            "accel_mag_std": mag_std,
            "accel_z_delta": z_delta,
            "accel_jerk": jerk,
            "gyro_mag_mean": gyro,
            "label": "Speed Breaker",
            "class_id": 1,
            "data_source": "synthetic"
        })

    # 3. Pothole (abrupt vertical drop, high shock impact, sharp jerk)
    for _ in range(num_samples_per_class):
        mag_mean = round(random.gauss(15.2, 1.2), 4)
        mag_max = round(random.gauss(21.5, 2.8), 4)
        mag_std = round(abs(random.gauss(5.8, 1.2)), 4)
        z_delta = round(abs(random.gauss(10.5, 2.5)), 4)
        jerk = round(abs(random.gauss(13.2, 3.2)), 4)
        gyro = round(abs(random.gauss(2.2, 0.6)), 4)
        rows.append({
            "accel_mag_mean": mag_mean,
            "accel_mag_max": mag_max,
            "accel_mag_std": mag_std,
            "accel_z_delta": z_delta,
            "accel_jerk": jerk,
            "gyro_mag_mean": gyro,
            "label": "Pothole",
            "class_id": 2,
            "data_source": "synthetic"
        })

    # Shuffle rows to avoid ordering bias
    random.shuffle(rows)

    fieldnames = [
        "accel_mag_mean",
        "accel_mag_max",
        "accel_mag_std",
        "accel_z_delta",
        "accel_jerk",
        "gyro_mag_mean",
        "label",
        "class_id",
        "data_source"
    ]

    with open(DATASET_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[SUCCESS] Generated {len(rows)} synthetic samples saved to {DATASET_PATH}")


if __name__ == "__main__":
    generate_synthetic_dataset()
