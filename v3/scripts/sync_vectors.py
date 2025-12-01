"""
Script to sync cards from SQLite to ChromaDB.

Reads all cards from the SQLite database and upserts them
into the ChromaDB vector store for semantic search.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.database.database_service import DatabaseService
from v3.database.card_repository import CardRepository
from v3.services.vector_service import VectorService
from v3.models.deck import MTGCard

def sync_vectors():
    print("Initializing services...")
    db_service = DatabaseService("v3/data/cards.db")
    vector_service = VectorService("v3/data/chroma_db")
    card_repo = CardRepository(db_service, vector_service=vector_service)
    
    print("Fetching cards from SQLite...")
    # Get all cards (using a broad search)
    # Note: In a real production system, we'd want a more efficient way to iterate
    # but for this scale, fetching all is fine.
    all_cards_data = db_service.search_cards(limit=10000)
    all_cards = [MTGCard(**c) for c in all_cards_data]
    
    print(f"Found {len(all_cards)} cards.")
    
    print("Generating embeddings and syncing to ChromaDB...")
    print("This may take a while depending on the number of cards...")
    
    count = vector_service.upsert_cards(all_cards)
    
    print(f"Successfully synced {count} cards to vector store.")
    print(f"Total cards in vector store: {vector_service.count()}")

if __name__ == "__main__":
    sync_vectors()
