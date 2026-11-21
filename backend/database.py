"""
Database Module for Road Quality Monitor
Handles SQLite database connection, table initialization, CRUD operations,
cryptographic verification queries, and aggregation statistics.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import config
from backend import crypto_utils


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection configured with Row factory."""
    db_path = Path(config.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(drop_existing: bool = False) -> None:
    """Initialize database tables and indexes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if drop_existing:
        cursor.execute("DROP TABLE IF EXISTS clusters")
        cursor.execute("DROP TABLE IF EXISTS detections")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        encrypted_device_id TEXT,
        timestamp TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        encrypted_latitude TEXT NOT NULL,
        encrypted_longitude TEXT NOT NULL,
        accel_x REAL DEFAULT 0.0,
        accel_y REAL DEFAULT 0.0,
        accel_z REAL DEFAULT 0.0,
        accel_mag REAL DEFAULT 0.0,
        peak_accel REAL DEFAULT 0.0,
        accel_variance REAL DEFAULT 0.0,
        gyro_mag REAL DEFAULT 0.0,
        event_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        pdi_score REAL NOT NULL,
        priority_level TEXT NOT NULL,
        cluster_id INTEGER DEFAULT -1,
        data_hash TEXT NOT NULL,
        digital_signature TEXT NOT NULL,
        is_simulated INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clusters (
        cluster_id INTEGER PRIMARY KEY,
        center_latitude REAL NOT NULL,
        center_longitude REAL NOT NULL,
        event_type TEXT NOT NULL,
        detection_count INTEGER NOT NULL,
        unique_devices INTEGER NOT NULL,
        avg_pdi_score REAL NOT NULL,
        max_pdi_score REAL NOT NULL,
        priority_level TEXT NOT NULL,
        last_reported_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Create helpful indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_event_type ON detections(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_priority ON detections(priority_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_cluster ON detections(cluster_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp)")

    conn.commit()
    conn.close()


def insert_detection(record: Dict[str, Any]) -> int:
    """
    Encrypt sensitive fields, compute SHA-256 hash and RSA digital signature,
    and insert detection record into the database.
    """
    device_id = str(record.get("device_id", "ANON-DEVICE"))
    timestamp = str(record.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()))
    lat = float(record.get("latitude", 0.0))
    lon = float(record.get("longitude", 0.0))
    event_type = str(record.get("event_type", "Normal Road"))
    confidence = float(record.get("confidence", 0.5))
    pdi_score = float(record.get("pdi_score", 0.0))
    priority_level = str(record.get("priority_level", "Low"))
    is_simulated = 1 if record.get("is_simulated", False) else 0

    accel_x = float(record.get("accel_x", 0.0))
    accel_y = float(record.get("accel_y", 0.0))
    accel_z = float(record.get("accel_z", 0.0))
    accel_mag = float(record.get("accel_mag", 0.0))
    peak_accel = float(record.get("peak_accel", 0.0))
    accel_variance = float(record.get("accel_variance", 0.0))
    gyro_mag = float(record.get("gyro_mag", 0.0))

    # 1. Encrypt sensitive fields using Fernet symmetric encryption
    encrypted_device_id = crypto_utils.encrypt_value(device_id)
    encrypted_latitude = crypto_utils.encrypt_value(f"{lat:.6f}")
    encrypted_longitude = crypto_utils.encrypt_value(f"{lon:.6f}")

    # 2. Build canonical string representation for integrity and signing
    canonical_data = {
        "device_id": device_id,
        "timestamp": timestamp,
        "latitude": lat,
        "longitude": lon,
        "event_type": event_type,
        "confidence": confidence,
        "pdi_score": pdi_score
    }
    canonical_str = crypto_utils.build_canonical_string(canonical_data)

    # 3. Compute SHA-256 hash
    data_hash = crypto_utils.compute_sha256(canonical_str)

    # 4. Generate RSA digital signature
    digital_signature = crypto_utils.sign_data(canonical_str)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections (
            device_id, encrypted_device_id, timestamp,
            latitude, longitude, encrypted_latitude, encrypted_longitude,
            accel_x, accel_y, accel_z, accel_mag, peak_accel, accel_variance, gyro_mag,
            event_type, confidence, pdi_score, priority_level, cluster_id,
            data_hash, digital_signature, is_simulated, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, -1, ?, ?, ?, ?)
    """, (
        device_id, encrypted_device_id, timestamp,
        lat, lon, encrypted_latitude, encrypted_longitude,
        accel_x, accel_y, accel_z, accel_mag, peak_accel, accel_variance, gyro_mag,
        event_type, confidence, pdi_score, priority_level,
        data_hash, digital_signature, is_simulated, now_iso
    ))

    inserted_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inserted_id


def get_all_detections(
    event_type: Optional[str] = None,
    priority: Optional[str] = None,
    is_simulated: Optional[int] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retrieve detections with optional filtering."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM detections WHERE 1=1"
    params = []

    if event_type and event_type != "All":
        query += " AND event_type = ?"
        params.append(event_type)

    if priority and priority != "All":
        query += " AND priority_level = ?"
        params.append(priority)

    if is_simulated is not None and is_simulated != -1:
        query += " AND is_simulated = ?"
        params.append(is_simulated)

    if search:
        query += " AND (device_id LIKE ? OR event_type LIKE ? OR priority_level LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    query += " ORDER BY id DESC"

    if limit and limit > 0:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results


def get_detection_by_id(detection_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single detection by primary key ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM detections WHERE id = ?", (detection_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_detection_by_id(detection_id: int) -> bool:
    """Delete single detection by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def delete_simulated_detections() -> int:
    """Delete all simulated/demo records from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections WHERE is_simulated = 1")
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


def clear_all_detections() -> None:
    """Completely wipe detections and clusters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections")
    cursor.execute("DELETE FROM clusters")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='detections'")
    conn.commit()
    conn.close()


def tamper_detection_for_demo(detection_id: int, field_to_alter: str = "pdi_score", new_value: Any = 99.9) -> Dict[str, Any]:
    """
    Intentionally alter a column directly in SQLite WITHOUT re-hashing or re-signing.
    Used for academic viva demonstration to show SHA-256 and RSA signature verification failure.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Allowed tamper fields
    allowed_fields = ["latitude", "longitude", "event_type", "confidence", "pdi_score", "device_id"]
    if field_to_alter not in allowed_fields:
        field_to_alter = "pdi_score"

    cursor.execute(f"UPDATE detections SET {field_to_alter} = ? WHERE id = ?", (new_value, detection_id))
    conn.commit()
    cursor.execute("SELECT * FROM detections WHERE id = ?", (detection_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}


def update_cluster_assignments(assignments: List[tuple], cluster_summaries: List[Dict[str, Any]]) -> None:
    """
    Update cluster_id on individual detections and populate clusters table.
    assignments: list of (cluster_id, detection_id)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update detection cluster_ids in bulk
    cursor.executemany("UPDATE detections SET cluster_id = ? WHERE id = ?", assignments)

    # Refresh clusters table
    cursor.execute("DELETE FROM clusters")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for c in cluster_summaries:
        cursor.execute("""
            INSERT INTO clusters (
                cluster_id, center_latitude, center_longitude, event_type,
                detection_count, unique_devices, avg_pdi_score, max_pdi_score,
                priority_level, last_reported_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c["cluster_id"],
            c["center_latitude"],
            c["center_longitude"],
            c["event_type"],
            c["detection_count"],
            c["unique_devices"],
            c["avg_pdi_score"],
            c["max_pdi_score"],
            c["priority_level"],
            c.get("last_reported_at", now_iso),
            now_iso
        ))

    conn.commit()
    conn.close()


def get_all_clusters() -> List[Dict[str, Any]]:
    """Retrieve all clustered location summaries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clusters ORDER BY max_pdi_score DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_dashboard_statistics() -> Dict[str, Any]:
    """Calculate real aggregated metrics from the local SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM detections")
    total_detections = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM detections WHERE event_type = 'Pothole'")
    total_potholes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM detections WHERE event_type = 'Speed Breaker'")
    total_speed_breakers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM detections WHERE event_type = 'Normal Road'")
    total_normal_roads = cursor.fetchone()[0]

    # Critical locations count
    cursor.execute("SELECT COUNT(*) FROM detections WHERE priority_level = 'Critical'")
    total_critical = cursor.fetchone()[0]

    # Distinct contributing devices
    cursor.execute("SELECT COUNT(DISTINCT device_id) FROM detections")
    unique_devices = cursor.fetchone()[0]

    # Priority breakdown
    cursor.execute("""
        SELECT priority_level, COUNT(*) as count
        FROM detections
        GROUP BY priority_level
    """)
    priority_counts = {row["priority_level"]: row["count"] for row in cursor.fetchall()}

    # Recent 10 detections
    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 10")
    recent_detections = [dict(row) for row in cursor.fetchall()]

    # Clustered hotspots
    cursor.execute("""
        SELECT cluster_id, center_latitude, center_longitude, event_type,
               detection_count, unique_devices, avg_pdi_score, priority_level
        FROM clusters
        WHERE priority_level IN ('High', 'Critical')
        ORDER BY detection_count DESC, max_pdi_score DESC
        LIMIT 5
    """)
    top_clusters = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "total_detections": total_detections,
        "total_potholes": total_potholes,
        "total_speed_breakers": total_speed_breakers,
        "total_normal_roads": total_normal_roads,
        "total_critical": total_critical,
        "unique_devices": unique_devices,
        "severity_distribution": {
            "Low": priority_counts.get("Low", 0),
            "Moderate": priority_counts.get("Moderate", 0),
            "High": priority_counts.get("High", 0),
            "Critical": priority_counts.get("Critical", 0)
        },
        "recent_detections": recent_detections,
        "top_hotspots": top_clusters
    }
