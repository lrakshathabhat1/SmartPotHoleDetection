"""
Database Initialization Script for Road Quality Monitor
Initializes SQLite database and creates detections and clusters tables.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import init_db


def main():
    drop = "--drop" in sys.argv
    print("=" * 60)
    print("Initializing Road Quality Monitor SQLite Database...")
    print("=" * 60)
    init_db(drop_existing=drop)
    print("[SUCCESS] Database tables created successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
