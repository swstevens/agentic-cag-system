#!/usr/bin/env python3
"""
Script to build the SQLite database from MTGJSON AllPrintings.json file

Usage:
    python -m mtg_cag_system.scripts.build_database
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mtg_cag_system.services.database_service import DatabaseService


def progress_callback(current, total):
    """Print progress updates"""
    percent = (current / total) * 100 if total > 0 else 0
    print(f"  Progress: {current:,}/{total:,} cards ({percent:.1f}%)", end='\r')


def main():
    print("=" * 70)
    print("MTG CAG System - Database Builder")
    print("=" * 70)
    print()

    # Paths
    json_path = "./data/mtgjson/AllPrintings.json"
    db_path = "./data/cards.db"

    # Check if JSON file exists
    if not os.path.exists(json_path):
        print(f"❌ Error: MTGJSON file not found at {json_path}")
        print()
        print("Please download AllPrintings.json from https://mtgjson.com/downloads/all-files/")
        print(f"and place it in: {json_path}")
        print()
        return 1

    # Check file size
    file_size = os.path.getsize(json_path) / (1024 * 1024)  # MB
    print(f"📁 Found MTGJSON file: {json_path}")
    print(f"   Size: {file_size:.1f} MB")
    print()

    # Warn if database already exists
    if os.path.exists(db_path):
        print(f"⚠️  Warning: Database already exists at {db_path}")
        response = input("   Overwrite? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return 0
        print()

    # Create database
    print(f"🔨 Creating database: {db_path}")
    db = DatabaseService(db_path)
    db.connect()

    # Initialize schema
    print("📋 Initializing database schema...")
    db.initialize_schema()
    print()

    # Load cards from JSON
    print(f"📚 Loading cards from {json_path}...")
    print("   This may take 2-5 minutes depending on your system...")
    print()

    try:
        card_count = db.load_from_mtgjson(json_path, progress_callback)
        print()  # New line after progress
        print()
        print("=" * 70)
        print(f"✅ Success! Database created with {card_count:,} cards")
        print(f"   Location: {db_path}")
        print(f"   Size: {os.path.getsize(db_path) / (1024 * 1024):.1f} MB")
        print("=" * 70)
        print()
        print("You can now start the server:")
        print("  python -m mtg_cag_system.main")
        print()

    except Exception as e:
        print()
        print(f"❌ Error loading cards: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
