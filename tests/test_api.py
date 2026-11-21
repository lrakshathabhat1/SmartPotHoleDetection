"""
Automated Integration and End-to-End API Tests for RoadQualityMonitor
Tests all Flask endpoints, database operations, tamper simulation, and CSV export.
"""

import sys
import unittest
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from backend import database


class TestAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        # Initialize fresh test database
        database.init_db(drop_existing=False)

    def test_dashboard_page_loads(self):
        """Test GET / loads frontend HTML with HTTP 200."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_stats_endpoint(self):
        """Test GET /api/stats returns valid schema."""
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("total_detections", data["data"])
        self.assertIn("severity_distribution", data["data"])

    def test_create_and_query_detection(self):
        """Test POST /api/detections ingests, classifies, signs, and hashes event."""
        payload = {
            "device_id": "TEST-UNIT-99",
            "timestamp": "2026-10-12T12:00:00Z",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accel_x": 0.1,
            "accel_y": 0.2,
            "accel_z": 16.5,
            "peak_accel": 22.0,
            "accel_variance": 25.0,
            "gyro_mag": 2.1,
            "is_simulated": True
        }
        res = self.client.post("/api/detections", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertTrue(data["success"])
        det_id = data["detection_id"]
        self.assertIn("event_type", data)
        self.assertIn("data_hash", data["cryptography"])
        self.assertIn("digital_signature_preview", data["cryptography"])

        # Fetch single detection
        fetch_res = self.client.get(f"/api/detections/{det_id}")
        self.assertEqual(fetch_res.status_code, 200)
        det_info = fetch_res.get_json()["data"]
        self.assertEqual(det_info["device_id"], "TEST-UNIT-99")
        self.assertTrue(det_info["verification"]["is_hash_valid"])
        self.assertTrue(det_info["verification"]["is_signature_valid"])

    def test_tamper_and_verify_workflow(self):
        """Test deliberate data tampering triggers cryptographic verification failure."""
        payload = {
            "device_id": "TAMPER-TEST-DEVICE",
            "latitude": 12.9500,
            "longitude": 77.6000,
            "accel_z": 9.8,
            "is_simulated": True
        }
        create_res = self.client.post("/api/detections", data=json.dumps(payload), content_type="application/json")
        det_id = create_res.get_json()["detection_id"]

        # Initial verify must pass
        verify_1 = self.client.post(f"/api/detections/{det_id}/verify")
        self.assertTrue(verify_1.get_json()["is_hash_valid"])
        self.assertTrue(verify_1.get_json()["is_signature_valid"])

        # Tamper with the record (alter pdi_score directly in DB)
        tamper_res = self.client.post(
            f"/api/detections/{det_id}/tamper",
            data=json.dumps({"field": "pdi_score", "value": 99.9}),
            content_type="application/json"
        )
        self.assertEqual(tamper_res.status_code, 200)

        # Verification after tampering MUST fail
        verify_2 = self.client.post(f"/api/detections/{det_id}/verify")
        res_data = verify_2.get_json()
        self.assertFalse(res_data["is_hash_valid"])
        self.assertFalse(res_data["is_signature_valid"])
        self.assertEqual(res_data["status"], "INTEGRITY_COMPROMISED")

    def test_csv_export(self):
        """Test GET /api/export/csv generates valid CSV download."""
        response = self.client.get("/api/export/csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["Content-Type"])
        self.assertIn("attachment; filename=road_quality_detections.csv", response.headers["Content-Disposition"])

    def test_empty_database_safety(self):
        """Test clearing the database and checking that statistics don't throw 500 error."""
        self.client.post("/api/detections/reset")
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["data"]["total_detections"], 0)


if __name__ == "__main__":
    unittest.main()
