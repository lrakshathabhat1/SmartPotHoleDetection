"""
Demonstration Data Seeder for Road Quality Monitor
Seeds realistic simulated road events across multiple distinct simulated vehicles
and realistic geographic clusters to showcase DBSCAN geospatial clustering,
crowdsourced agreement, PDI scoring, and cryptographic security.
"""

import sys
import random
import datetime
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import database, detection, clustering

# Sample geographic hotspots (Bengaluru urban road network)
HOTSPOTS = [
    {
        "name": "Outer Ring Road - Bellandur Junction",
        "center_lat": 12.9279,
        "center_lon": 77.6835,
        "type": "Pothole",
        "passes": 5,
        "devices": ["DEV-CAB-101", "DEV-BUS-204", "DEV-CAR-309", "DEV-BIKE-044", "DEV-AUTO-501"],
        "accel_profile": {"mag_mean": 15.8, "peak": 22.4, "variance": 36.0, "gyro": 2.4}
    },
    {
        "name": "Old Airport Road - Kodihalli Stretch",
        "center_lat": 12.9601,
        "center_lon": 77.6482,
        "type": "Pothole",
        "passes": 4,
        "devices": ["DEV-CAB-102", "DEV-CAR-312", "DEV-AUTO-503", "DEV-VAN-802"],
        "accel_profile": {"mag_mean": 14.5, "peak": 19.8, "variance": 28.5, "gyro": 1.9}
    },
    {
        "name": "Indiranagar 100ft Road - Traffic Calming Zone",
        "center_lat": 12.9784,
        "center_lon": 77.6408,
        "type": "Speed Breaker",
        "passes": 4,
        "devices": ["DEV-BUS-201", "DEV-CAR-309", "DEV-AUTO-502", "DEV-CAB-105"],
        "accel_profile": {"mag_mean": 11.8, "peak": 14.2, "variance": 4.5, "gyro": 1.2}
    },
    {
        "name": "Koramangala 4th Block - School Cross",
        "center_lat": 12.9352,
        "center_lon": 77.6245,
        "type": "Speed Breaker",
        "passes": 3,
        "devices": ["DEV-VAN-801", "DEV-CAR-315", "DEV-BIKE-045"],
        "accel_profile": {"mag_mean": 11.2, "peak": 13.6, "variance": 3.8, "gyro": 0.9}
    },
    {
        "name": "Cubbon Park Road - Freshly Paved Corridor",
        "center_lat": 12.9766,
        "center_lon": 77.5993,
        "type": "Normal Road",
        "passes": 4,
        "devices": ["DEV-CAB-101", "DEV-CAR-312", "DEV-BUS-204", "DEV-VAN-801"],
        "accel_profile": {"mag_mean": 9.8, "peak": 10.1, "variance": 0.1, "gyro": 0.05}
    },
    {
        "name": "Residency Road - Smooth Highway Transit",
        "center_lat": 12.9680,
        "center_lon": 77.6020,
        "type": "Normal Road",
        "passes": 3,
        "devices": ["DEV-AUTO-501", "DEV-CAB-102", "DEV-BIKE-044"],
        "accel_profile": {"mag_mean": 9.75, "peak": 10.05, "variance": 0.08, "gyro": 0.04}
    }
]


def run_seed():
    print("=" * 65)
    print("Seeding Realistic Multi-Vehicle Demonstration Road Quality Data...")
    print("=" * 65)

    base_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)
    total_seeded = 0

    for spot in HOTSPOTS:
        print(f"[SEED] Generating cluster for: {spot['name']} ({spot['type']})")
        passes = spot["passes"]
        devices = spot["devices"]
        prof = spot["accel_profile"]

        for i in range(passes):
            device_id = devices[i % len(devices)]
            # Small realistic GPS jitter (within ~15-25 meters)
            lat_jitter = random.uniform(-0.00015, 0.00015)
            lon_jitter = random.uniform(-0.00015, 0.00015)
            lat = round(spot["center_lat"] + lat_jitter, 6)
            lon = round(spot["center_lon"] + lon_jitter, 6)

            # Kinematic profile with slight variance
            peak = round(prof["peak"] + random.uniform(-0.6, 0.6), 2)
            mag = round(prof["mag_mean"] + random.uniform(-0.3, 0.3), 2)
            variance = round(max(0.05, prof["variance"] + random.uniform(-0.5, 0.5)), 2)
            gyro = round(max(0.02, prof["gyro"] + random.uniform(-0.1, 0.1)), 2)

            event_time = base_time + datetime.timedelta(minutes=random.randint(5, 300))

            payload = {
                "device_id": device_id,
                "timestamp": event_time.isoformat(),
                "latitude": lat,
                "longitude": lon,
                "accel_x": round(random.uniform(-0.8, 0.8), 2),
                "accel_y": round(random.uniform(-0.8, 0.8), 2),
                "accel_z": round(mag, 2),
                "peak_accel": peak,
                "accel_variance": variance,
                "gyro_mag": gyro,
                "is_simulated": True
            }

            detection.process_sensor_event(payload, trigger_clustering=False)
            total_seeded += 1

    # Now run clustering over all seeded points
    clusters = clustering.recalculate_and_save_clusters()
    print(f"\n[SUCCESS] Seeded {total_seeded} detections into database.")
    print(f"[SUCCESS] DBSCAN grouped detections into {len(clusters)} distinct geographic clusters.")
    print("=" * 65)
    return total_seeded


def main():
    database.init_db()
    run_seed()


if __name__ == "__main__":
    main()
