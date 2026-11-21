"""
Main Flask Application Entrypoint for RoadQualityMonitor
Secure Crowdsourced Road Quality Monitoring and Pothole Severity Detection System
"""

import os
import sys
from pathlib import Path
from flask import Flask
from flask_cors import CORS
import config
from backend.database import init_db
from backend.routes import api_bp
from backend import crypto_utils
from ml import predict


def create_app():
    """Application factory for Road Quality Monitor."""
    app = Flask(
        __name__,
        template_folder=str(config.BASE_DIR / "frontend" / "templates"),
        static_folder=str(config.BASE_DIR / "frontend" / "static")
    )
    app.config["SECRET_KEY"] = config.SECRET_KEY
    CORS(app)

    # Register blueprints
    app.register_blueprint(api_bp)

    # Initialize components
    with app.app_context():
        # Ensure database tables exist
        init_db(drop_existing=False)

        # Ensure cryptographic keys exist
        crypto_utils._ensure_keys_exist()

        # Warm up machine learning model
        predict.load_model_and_scaler()

    return app


app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

    print("\n" + "=" * 70)
    print(" ROAD QUALITY MONITOR & POTHOLE SEVERITY DETECTION SYSTEM")
    print(" 5th-Semester CSE Engineering Mini-Project Prototype")
    print("=" * 70)
    print(f" * Server running on: http://{host}:{port}/")
    print(" * Open this URL in your web browser (Chrome, Edge, Firefox)")
    print(" * Press Ctrl+C in this terminal to stop the server")
    print("=" * 70 + "\n")

    app.run(host=host, port=port, debug=debug)
