"""
Automated Unit Tests for Machine Learning and Preprocessing
Tests:
1. Feature extraction from raw multi-axis sensor data.
2. Random Forest prediction output format and probabilities.
3. Correct classification behavior for distinct kinematic profiles.
4. Model metadata verification.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import preprocessing
from ml import predict


class TestMachineLearning(unittest.TestCase):

    def setUp(self):
        predict.load_model_and_scaler()

    def test_feature_extraction_from_readings(self):
        """Test statistical feature extraction from a window of sensor readings."""
        raw_samples = [
            {"x": 0.1, "y": 0.2, "z": 9.8, "gx": 0.01, "gy": 0.02, "gz": 0.01},
            {"x": 0.2, "y": -0.1, "z": 10.1, "gx": 0.02, "gy": 0.01, "gz": 0.01},
            {"x": -0.1, "y": 0.1, "z": 9.7, "gx": 0.01, "gy": 0.01, "gz": 0.02}
        ]
        feats = preprocessing.extract_features_from_window(raw_samples)
        for col in preprocessing.FEATURE_COLUMNS:
            self.assertIn(col, feats)
            self.assertIsInstance(feats[col], (int, float))

    def test_normal_road_prediction(self):
        """Test that smooth kinematic values classify as Normal Road."""
        features = {
            "accel_mag_mean": 9.81,
            "accel_mag_max": 10.05,
            "accel_mag_std": 0.15,
            "accel_z_delta": 0.20,
            "accel_jerk": 0.35,
            "gyro_mag_mean": 0.05
        }
        result = predict.predict_road_event(features)
        self.assertEqual(result["event_type"], "Normal Road")
        self.assertEqual(result["class_id"], 0)
        self.assertGreaterEqual(result["confidence"], 0.70)

    def test_pothole_prediction(self):
        """Test that sharp vertical shock impact classifies as Pothole."""
        features = {
            "accel_mag_mean": 16.5,
            "accel_mag_max": 24.2,
            "accel_mag_std": 6.8,
            "accel_z_delta": 14.1,
            "accel_jerk": 15.6,
            "gyro_mag_mean": 2.5
        }
        result = predict.predict_road_event(features)
        self.assertEqual(result["event_type"], "Pothole")
        self.assertEqual(result["class_id"], 2)
        self.assertGreaterEqual(result["confidence"], 0.70)

    def test_speed_breaker_prediction(self):
        """Test that smooth rise and moderate rocking pitch classifies as Speed Breaker."""
        features = {
            "accel_mag_mean": 11.4,
            "accel_mag_max": 13.9,
            "accel_mag_std": 2.1,
            "accel_z_delta": 4.0,
            "accel_jerk": 3.0,
            "gyro_mag_mean": 1.2
        }
        result = predict.predict_road_event(features)
        self.assertEqual(result["event_type"], "Speed Breaker")
        self.assertEqual(result["class_id"], 1)
        self.assertGreaterEqual(result["confidence"], 0.70)


if __name__ == "__main__":
    unittest.main()
