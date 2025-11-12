#!/usr/bin/env python3
"""
Build Synergy-Focused Embeddings for MTG Cards

This script orchestrates the complete workflow for creating synergy-focused embeddings:
1. Extract synergy patterns from card oracle text
2. Build vector embeddings that incorporate synergy signals
3. Create searchable vector store for synergy lookup

This is a convenience script that runs the full pipeline in order.

Usage:
    python scripts/build_synergy_embeddings.py

To rebuild embeddings with new patterns:
    python scripts/build_synergy_embeddings.py --force-rebuild

Steps:
    1. Extracts synergy patterns from all cards (via extract_synergy_patterns.py)
    2. Builds embeddings with synergy signals (via VectorStoreService)
    3. Creates ChromaDB collection with persistent storage
"""

import sys
import argparse
import logging
from pathlib import Path
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd: list, description: str) -> bool:
    """Run a command and report results"""
    logger.info(f"\n{'='*70}")
    logger.info(f"Step: {description}")
    logger.info(f"{'='*70}")

    try:
        result = subprocess.run(cmd, check=True)
        logger.info(f"✅ {description} - SUCCESS\n")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - FAILED")
        logger.error(f"   Exit code: {e.returncode}")
        return False


def check_database(db_path: str) -> bool:
    """Check if the card database exists"""
    if not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}")
        logger.error("Please run: python scripts/load_atomic_cards.py")
        return False
    logger.info(f"✅ Database found at {db_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Build synergy-focused embeddings for MTG cards"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="./data/cards_atomic.db",
        help="Path to the cards database",
    )
    parser.add_argument(
        "--patterns-output",
        type=str,
        default="./data/synergy_patterns.json",
        help="Path to output synergy patterns",
    )
    parser.add_argument(
        "--chroma-dir",
        type=str,
        default="./data/chroma",
        help="Directory for ChromaDB storage",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Force rebuild even if embeddings exist",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip synergy pattern extraction (use existing patterns)",
    )

    args = parser.parse_args()

    logger.info("\n" + "="*70)
    logger.info("MTG SYNERGY-FOCUSED EMBEDDINGS BUILD PIPELINE")
    logger.info("="*70)

    # Step 0: Check prerequisites
    logger.info("\nStep 0: Checking prerequisites...")
    if not check_database(args.db):
        return False

    # Step 1: Extract synergy patterns (if not skipped)
    if not args.skip_extraction:
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "extract_synergy_patterns.py"),
            "--db", args.db,
            "--output", args.patterns_output,
        ]
        if not run_command(cmd, "Extract synergy patterns from oracle text"):
            logger.error("Failed to extract synergy patterns. Aborting.")
            return False
    else:
        logger.info("Skipping synergy pattern extraction (using existing patterns)")

    # Step 2: Build embeddings with synergy signals
    logger.info(f"\n{'='*70}")
    logger.info("Step 2: Build embeddings with synergy signals")
    logger.info(f"{'='*70}")

    try:
        # Import required modules
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from mtg_cag_system.services.database_service import DatabaseService
        from mtg_cag_system.services.vector_store_service import VectorStoreService

        # Connect to database
        logger.info(f"Connecting to database at {args.db}...")
        db = DatabaseService(args.db)
        db.connect()
        card_count = db.card_count()
        logger.info(f"✅ Database connected ({card_count:,} cards)")

        # Initialize vector store with synergy patterns
        logger.info(f"Initializing vector store with synergy patterns...")
        vector_store = VectorStoreService(
            persist_directory=args.chroma_dir,
            synergy_patterns_path=args.patterns_output
        )

        if vector_store.synergy_patterns:
            logger.info(f"✅ Loaded {len(vector_store.synergy_patterns)} synergy patterns")
        else:
            logger.warning("⚠️  No synergy patterns loaded (continuing with standard embeddings)")

        # Build embeddings
        logger.info("Building embeddings (this may take several minutes)...")
        vector_store.build_embeddings(
            database_service=db,
            batch_size=1000,
            force_rebuild=args.force_rebuild
        )

        db.disconnect()
        logger.info("✅ Embeddings built successfully")

    except Exception as e:
        logger.error(f"❌ Failed to build embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Summary
    logger.info("\n" + "="*70)
    logger.info("BUILD PIPELINE COMPLETE")
    logger.info("="*70)
    logger.info(f"Synergy patterns:    {args.patterns_output}")
    logger.info(f"Vector embeddings:   {args.chroma_dir}")
    logger.info(f"Database:            {args.db}")
    logger.info("\nYou can now use the synergy lookup endpoint:")
    logger.info("  ./scripts/synergy_lookup.sh \"Lightning Bolt\" 10 Modern")
    logger.info("="*70 + "\n")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
