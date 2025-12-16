"""
Script to sync cards from SQLite to ChromaDB.

Reads all cards from the SQLite database and upserts them
into the ChromaDB vector store for semantic search.
"""

import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add parent directory to path
# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # v3 folder
project_root = os.path.dirname(parent_dir) # root folder
sys.path.append(project_root)

from v3.database.database_service import DatabaseService
from v3.database.card_repository import CardRepository
from v3.services.vector_service import VectorService
from v3.models.deck import MTGCard

def sync_vectors():
    logger.info("Initializing services...")
    
    # Use absolute paths based on script location to avoid "v3/v3" issues
    # Script is in v3/scripts/, so we want v3/data/
    data_dir = os.path.join(parent_dir, "data")
    db_path = os.path.join(data_dir, "cards.db")
    chroma_path = os.path.join(data_dir, "chroma_db")
    
    logger.info(f"Using database at: {db_path}")
    logger.info(f"Using chroma at: {chroma_path}")

    db_service = DatabaseService(db_path)
    vector_service = VectorService(chroma_path)
    card_repo = CardRepository(db_service, vector_service=vector_service)
    
    logger.info("Fetching cards from SQLite...")
    # Get all cards (using a broad search)
    all_cards_data = db_service.search_cards(limit=10000)
    all_cards = [MTGCard(**c) for c in all_cards_data]
    
    logger.info(f"Found {len(all_cards)} cards.")
    
    logger.info("Generating embeddings and syncing to ChromaDB...")
    logger.info("This may take a while depending on the number of cards...")
    
    count = vector_service.upsert_cards(all_cards)
    
    logger.info(f"Successfully synced {count} cards to vector store.")
    logger.info(f"Total cards in vector store: {vector_service.count()}")

if __name__ == "__main__":
    sync_vectors()
