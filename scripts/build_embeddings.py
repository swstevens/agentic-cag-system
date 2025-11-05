#!/usr/bin/env python3
"""
One-time script to build vector embeddings for all MTG cards

This script:
1. Loads all cards from the database
2. Generates embeddings using sentence transformers
3. Saves embeddings to disk in ChromaDB
4. Only needs to be run once (or when database is updated)

Usage:
    python scripts/build_embeddings.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.vector_store_service import VectorStoreService


def progress_callback(current: int, total: int):
    """Print progress bar"""
    percent = (current / total) * 100
    bar_length = 50
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f'\r[{bar}] {percent:.1f}% ({current}/{total} cards)', end='', flush=True)


def main():
    print("=" * 80)
    print("MTG Card Vector Embeddings Builder")
    print("=" * 80)
    print()

    # Initialize database (using AtomicCards database)
    print("📀 Connecting to database...")
    db = DatabaseService(db_path="./data/cards_atomic.db")
    db.connect()

    card_count = db.card_count()
    print(f"   Found {card_count:,} cards in database")
    print()

    # Initialize vector store
    print("🔮 Initializing vector store...")
    vector_store = VectorStoreService(
        persist_directory="./data/chroma",
        collection_name="mtg_cards"
    )

    if vector_store.is_initialized():
        print("   ⚠️  Embeddings already exist!")
        print(f"   Current count: {vector_store.collection.count():,} embeddings")
        print()
        response = input("   Do you want to rebuild? This will delete existing embeddings. (y/N): ")
        if response.lower() != 'y':
            print("   Cancelled.")
            return

        # Delete existing collection
        print("   Deleting existing collection...")
        vector_store.client.delete_collection(name="mtg_cards")
        vector_store = VectorStoreService(
            persist_directory="./data/chroma",
            collection_name="mtg_cards"
        )

    print()
    print("🚀 Building embeddings...")
    print("   This may take 10-30 minutes depending on your hardware.")
    print("   Embeddings will be saved to disk and reused in future runs.")
    print()

    start_time = time.time()

    # Build embeddings with progress callback
    try:
        vector_store.build_embeddings(
            database_service=db,
            batch_size=1000,
            progress_callback=progress_callback
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Build interrupted by user")
        print("   Partial embeddings have been saved and will be resumed next time.")
        return
    except Exception as e:
        print(f"\n\n❌ Error building embeddings: {e}")
        raise

    print()  # New line after progress bar
    print()

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("=" * 80)
    print("✅ EMBEDDINGS BUILD COMPLETE")
    print("=" * 80)
    print(f"Total cards: {vector_store.collection.count():,}")
    print(f"Time elapsed: {minutes}m {seconds}s")
    print(f"Storage location: {vector_store.persist_directory}")
    print()
    print("You can now use similarity search in your deck builder!")
    print()

    # Test the embeddings
    print("🔍 Testing similarity search...")
    similar = vector_store.find_similar_cards("Llanowar Elves", n_results=5)
    print("   Cards similar to 'Llanowar Elves':")
    for card in similar:
        print(f"      - {card['name']} (similarity: {1 - card['distance']:.3f})")

    print()
    print("🎉 All done!")

    db.disconnect()


if __name__ == "__main__":
    main()
