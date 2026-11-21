"""
Flask API Routes and Web Endpoints for Road Quality Monitor
Provides REST API endpoints for sensor ingestion, data querying,
cryptographic verification, DBSCAN clustering, CSV export, and demo management.
"""

import io
import csv
from flask import Blueprint, request, jsonify, render_template, Response, make_response
from backend import database, detection, clustering, crypto_utils, severity
import config

api_bp = Blueprint("api", __name__)


# ----------------------------------------------------------------------
# 1. Page Route
# ----------------------------------------------------------------------

@api_bp.route("/")
def index():
    """Render main dashboard view."""
    return render_template("index.html")


# ----------------------------------------------------------------------
# 2. Dashboard Statistics & Overview
# ----------------------------------------------------------------------

@api_bp.route("/api/stats", methods=["GET"])
def get_stats():
    """Return live dashboard statistics computed from SQLite."""
    try:
        stats = database.get_dashboard_statistics()
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ----------------------------------------------------------------------
# 3. Detection Ingestion & Querying
# ----------------------------------------------------------------------

@api_bp.route("/api/detections", methods=["GET"])
def list_detections():
    """Fetch detections with optional filters."""
    event_type = request.args.get("event_type")
    priority = request.args.get("priority")
    search = request.args.get("search")
    is_simulated = request.args.get("is_simulated", type=int)
    limit = request.args.get("limit", default=100, type=int)

    records = database.get_all_detections(
        event_type=event_type,
        priority=priority,
        is_simulated=is_simulated,
        search=search,
        limit=limit
    )
    return jsonify({"success": True, "count": len(records), "data": records})


@api_bp.route("/api/detections", methods=["POST"])
def create_detection():
    """Ingest new sensor event, classify, cryptographically secure, and persist."""
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"success": False, "error": "Invalid or missing JSON payload"}), 400

    try:
        result = detection.process_sensor_event(payload, trigger_clustering=True)
        return jsonify(result), 201
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to process sensor event: {str(e)}"}), 500


@api_bp.route("/api/detections/<int:detection_id>", methods=["GET"])
def get_detection(detection_id):
    """Fetch single detection record with cryptographic and decrypted details."""
    record = database.get_detection_by_id(detection_id)
    if not record:
        return jsonify({"success": False, "error": "Detection not found"}), 404

    # Perform live cryptographic verification on fetch
    canonical_data = {
        "device_id": record["device_id"],
        "timestamp": record["timestamp"],
        "latitude": record["latitude"],
        "longitude": record["longitude"],
        "event_type": record["event_type"],
        "confidence": record["confidence"],
        "pdi_score": record["pdi_score"]
    }
    canonical_str = crypto_utils.build_canonical_string(canonical_data)
    hash_valid = crypto_utils.verify_sha256(canonical_str, record["data_hash"])
    sig_valid = crypto_utils.verify_signature(canonical_str, record["digital_signature"])

    # Decrypt coordinates for authorized inspection
    decrypted_lat = crypto_utils.decrypt_value(record["encrypted_latitude"])
    decrypted_lon = crypto_utils.decrypt_value(record["encrypted_longitude"])
    decrypted_device = crypto_utils.decrypt_value(record["encrypted_device_id"])

    response_data = dict(record)
    response_data["verification"] = {
        "canonical_string": canonical_str,
        "is_hash_valid": hash_valid,
        "is_signature_valid": sig_valid,
        "decrypted_latitude": decrypted_lat,
        "decrypted_longitude": decrypted_lon,
        "decrypted_device_id": decrypted_device
    }

    return jsonify({"success": True, "data": response_data})


@api_bp.route("/api/detections/<int:detection_id>", methods=["DELETE"])
def delete_detection(detection_id):
    """Delete a single detection record."""
    deleted = database.delete_detection_by_id(detection_id)
    if not deleted:
        return jsonify({"success": False, "error": "Detection record not found"}), 404

    # Recalculate clusters after deletion
    clustering.recalculate_and_save_clusters()
    return jsonify({"success": True, "message": f"Detection {detection_id} deleted successfully."})


@api_bp.route("/api/detections/simulated", methods=["DELETE"])
def delete_simulated():
    """Delete all simulated/demo records."""
    count = database.delete_simulated_detections()
    clustering.recalculate_and_save_clusters()
    return jsonify({"success": True, "deleted_count": count, "message": f"Deleted {count} simulated records."})


@api_bp.route("/api/detections/reset", methods=["POST"])
def reset_database_data():
    """Clear all records and reinitialize empty tables."""
    database.clear_all_detections()
    return jsonify({"success": True, "message": "Database successfully wiped."})


# ----------------------------------------------------------------------
# 4. Cryptographic Tamper & Verification Demonstration Endpoints
# ----------------------------------------------------------------------

@api_bp.route("/api/detections/<int:detection_id>/verify", methods=["POST"])
def verify_detection_crypto(detection_id):
    """
    On-demand cryptographic integrity and signature verification.
    Demonstrates checking SHA-256 hash matching and RSA public-key verification.
    """
    record = database.get_detection_by_id(detection_id)
    if not record:
        return jsonify({"success": False, "error": "Detection not found"}), 404

    canonical_data = {
        "device_id": record["device_id"],
        "timestamp": record["timestamp"],
        "latitude": record["latitude"],
        "longitude": record["longitude"],
        "event_type": record["event_type"],
        "confidence": record["confidence"],
        "pdi_score": record["pdi_score"]
    }
    canonical_str = crypto_utils.build_canonical_string(canonical_data)

    hash_valid = crypto_utils.verify_sha256(canonical_str, record["data_hash"])
    sig_valid = crypto_utils.verify_signature(canonical_str, record["digital_signature"])

    return jsonify({
        "success": True,
        "detection_id": detection_id,
        "is_hash_valid": hash_valid,
        "is_signature_valid": sig_valid,
        "current_computed_hash": crypto_utils.compute_sha256(canonical_str),
        "stored_hash": record["data_hash"],
        "status": "SECURE_AND_VERIFIED" if (hash_valid and sig_valid) else "INTEGRITY_COMPROMISED"
    })


@api_bp.route("/api/detections/<int:detection_id>/tamper", methods=["POST"])
def tamper_detection(detection_id):
    """
    Intentionally alter a record's data directly in the database without updating hash or signature.
    Enables live demonstration of cryptographic tamper detection during viva presentation.
    """
    payload = request.get_json(silent=True) or {}
    field = payload.get("field", "pdi_score")
    value = payload.get("value", 99.9)

    tampered_record = database.tamper_detection_for_demo(detection_id, field_to_alter=field, new_value=value)
    if not tampered_record:
        return jsonify({"success": False, "error": "Detection not found"}), 404

    return jsonify({
        "success": True,
        "message": f"Record {detection_id} field '{field}' intentionally modified to {value}.",
        "instruction": "Click 'Verify Cryptography' to observe SHA-256 mismatch and RSA signature failure."
    })


# ----------------------------------------------------------------------
# 5. Geospatial Clustering Endpoints
# ----------------------------------------------------------------------

@api_bp.route("/api/clusters", methods=["GET"])
def get_clusters():
    """Retrieve all current DBSCAN clusters."""
    clusters = database.get_all_clusters()
    return jsonify({"success": True, "count": len(clusters), "data": clusters})


@api_bp.route("/api/detections/recluster", methods=["POST"])
def trigger_recluster():
    """Trigger on-demand DBSCAN clustering recalculation."""
    payload = request.get_json(silent=True) or {}
    eps_km = payload.get("eps_km", config.DBSCAN_EPS_KM)
    min_samples = payload.get("min_samples", config.DBSCAN_MIN_SAMPLES)

    clusters = clustering.recalculate_and_save_clusters(eps_km=eps_km, min_samples=min_samples)
    return jsonify({"success": True, "cluster_count": len(clusters), "data": clusters})


# ----------------------------------------------------------------------
# 6. Machine Learning Metadata
# ----------------------------------------------------------------------

@api_bp.route("/api/ml/info", methods=["GET"])
def get_ml_info():
    """Return ML model metadata, accuracy, and synthetic dataset disclaimer."""
    from pathlib import Path
    import json
    metadata_path = Path(config.METADATA_PATH)
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return jsonify({"success": True, "metadata": metadata})
    return jsonify({"success": False, "message": "Model not trained yet."}), 404


# ----------------------------------------------------------------------
# 7. CSV Export
# ----------------------------------------------------------------------

@api_bp.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Export all detections as a downloadable CSV file."""
    detections = database.get_all_detections()

    output = io.StringIO()
    fieldnames = [
        "id", "device_id", "timestamp", "latitude", "longitude",
        "accel_mag", "peak_accel", "gyro_mag", "event_type",
        "confidence", "pdi_score", "priority_level", "cluster_id",
        "data_hash", "digital_signature", "is_simulated", "created_at"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in detections:
        writer.writerow(row)

    csv_data = output.getvalue()
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=road_quality_detections.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response


# ----------------------------------------------------------------------
# 8. Demonstration Dataset Seeder Endpoint
# ----------------------------------------------------------------------

@api_bp.route("/api/demo/seed", methods=["POST"])
def seed_demo_data():
    """Seed realistic demonstration clusters and events."""
    from scripts.seed_demo_data import run_seed
    seeded_count = run_seed()
    clustering.recalculate_and_save_clusters()
    return jsonify({
        "success": True,
        "seeded_count": seeded_count,
        "message": f"Successfully seeded {seeded_count} realistic demonstration events across multiple vehicle passes."
    })
