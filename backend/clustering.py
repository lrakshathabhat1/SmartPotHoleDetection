"""
Geospatial Clustering Module using DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
Groups nearby road quality detections using great-circle Haversine distance,
synthesizes crowdsourced vehicle observations, and identifies persistent road distress hotspots.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.cluster import DBSCAN

import config
from backend import database, severity


def perform_dbscan_clustering(
    detections: List[Dict[str, Any]],
    eps_km: float = None,
    min_samples: int = None
) -> Tuple[List[tuple], List[Dict[str, Any]]]:
    """
    Run DBSCAN clustering with Haversine metric on detection GPS coordinates.
    Returns:
    - assignments: list of (cluster_id, detection_id) tuples
    - cluster_summaries: list of summary dicts for each formed cluster
    """
    if not detections:
        return [], []

    if eps_km is None:
        eps_km = config.DBSCAN_EPS_KM
    if min_samples is None:
        min_samples = config.DBSCAN_MIN_SAMPLES

    # Convert eps from kilometers to radians on Earth
    eps_rad = eps_km / config.EARTH_RADIUS_KM

    # Extract coordinates in radians for haversine metric
    # Note: Scikit-learn haversine expects coordinates in (lat, lon) order in radians
    coords_deg = np.array([[d["latitude"], d["longitude"]] for d in detections], dtype=np.float64)
    coords_rad = np.radians(coords_deg)

    # Run DBSCAN
    db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine")
    labels = db.fit_predict(coords_rad)

    assignments = []
    cluster_groups: Dict[int, List[Dict[str, Any]]] = {}

    for idx, d in enumerate(detections):
        cluster_id = int(labels[idx])
        assignments.append((cluster_id, d["id"]))

        if cluster_id != -1:  # -1 is noise in DBSCAN
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(d)

    # Build cluster summary objects
    summaries = []
    for c_id, members in cluster_groups.items():
        lats = [m["latitude"] for m in members]
        lons = [m["longitude"] for m in members]
        device_ids = set(m["device_id"] for m in members)
        event_types = [m["event_type"] for m in members]
        pdi_scores = [float(m["pdi_score"]) for m in members]
        timestamps = [m["timestamp"] for m in members]

        # Center coordinates
        center_lat = round(float(np.mean(lats)), 6)
        center_lon = round(float(np.mean(lons)), 6)

        # Dominant event type (prefer Pothole > Speed Breaker > Normal Road if tie)
        severity_rank = {"Pothole": 3, "Speed Breaker": 2, "Normal Road": 1}
        dominant_type = max(set(event_types), key=lambda t: (event_types.count(t), severity_rank.get(t, 0)))

        det_count = len(members)
        unique_dev_count = len(device_ids)

        # Composite cluster PDI score
        cluster_pdi, priority = severity.calculate_cluster_pdi(
            base_scores=pdi_scores,
            detection_count=det_count,
            unique_devices_count=unique_dev_count,
            dominant_event_type=dominant_type
        )

        last_reported = max(timestamps) if timestamps else ""

        summaries.append({
            "cluster_id": c_id,
            "center_latitude": center_lat,
            "center_longitude": center_lon,
            "event_type": dominant_type,
            "detection_count": det_count,
            "unique_devices": unique_dev_count,
            "avg_pdi_score": round(float(np.mean(pdi_scores)), 1),
            "max_pdi_score": cluster_pdi,
            "priority_level": priority,
            "last_reported_at": last_reported
        })

    return assignments, summaries


def recalculate_and_save_clusters(eps_km: float = None, min_samples: int = None) -> List[Dict[str, Any]]:
    """
    Fetch all detections from database, run DBSCAN, and persist cluster assignments.
    """
    detections = database.get_all_detections()
    if not detections:
        database.update_cluster_assignments([], [])
        return []

    assignments, summaries = perform_dbscan_clustering(
        detections=detections,
        eps_km=eps_km,
        min_samples=min_samples
    )

    database.update_cluster_assignments(assignments, summaries)
    return summaries
