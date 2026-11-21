"""
Automated Unit Tests for Geospatial Clustering (DBSCAN)
Tests:
1. Spatial grouping of close-proximity detections into clusters.
2. Noise detection for distant outliers.
3. Multi-device consensus calculation.
4. Graceful handling of empty datasets.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import clustering


class TestGeospatialClustering(unittest.TestCase):

    def test_empty_clustering(self):
        """Test clustering with empty input list."""
        assignments, summaries = clustering.perform_dbscan_clustering([])
        self.assertEqual(assignments, [])
        self.assertEqual(summaries, [])

    def test_cluster_nearby_detections(self):
        """Test that detections within 30 meters from different vehicles form a cluster."""
        # MG Road coordinates ~ 12.9750, 77.6090
        # ~10-15 meter offsets
        detections = [
            {
                "id": 1,
                "device_id": "CAR-01",
                "latitude": 12.97500,
                "longitude": 77.60900,
                "event_type": "Pothole",
                "pdi_score": 80.0,
                "timestamp": "2026-10-12T10:00:00Z"
            },
            {
                "id": 2,
                "device_id": "CAB-02",
                "latitude": 12.97508,
                "longitude": 77.60905,
                "event_type": "Pothole",
                "pdi_score": 85.0,
                "timestamp": "2026-10-12T10:05:00Z"
            },
            {
                "id": 3,
                "device_id": "BIKE-03",
                "latitude": 12.97505,
                "longitude": 77.60902,
                "event_type": "Pothole",
                "pdi_score": 82.0,
                "timestamp": "2026-10-12T10:10:00Z"
            },
            # Outlier 2 km away
            {
                "id": 4,
                "device_id": "CAR-04",
                "latitude": 12.99500,
                "longitude": 77.62500,
                "event_type": "Normal Road",
                "pdi_score": 10.0,
                "timestamp": "2026-10-12T10:15:00Z"
            }
        ]

        # eps_km = 0.05 (50 meters), min_samples = 2
        assignments, summaries = clustering.perform_dbscan_clustering(
            detections,
            eps_km=0.05,
            min_samples=2
        )

        # There should be exactly 1 formed cluster
        self.assertEqual(len(summaries), 1)
        cluster = summaries[0]
        self.assertEqual(cluster["detection_count"], 3)
        self.assertEqual(cluster["unique_devices"], 3)
        self.assertEqual(cluster["event_type"], "Pothole")
        self.assertGreaterEqual(cluster["max_pdi_score"], 80.0)

        # Check that outlier ID 4 is noise (cluster_id == -1)
        assignment_map = dict([(det_id, c_id) for c_id, det_id in assignments])
        self.assertEqual(assignment_map[4], -1)
        self.assertEqual(assignment_map[1], 0)
        self.assertEqual(assignment_map[2], 0)
        self.assertEqual(assignment_map[3], 0)


if __name__ == "__main__":
    unittest.main()
