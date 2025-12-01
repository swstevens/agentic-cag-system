"""
Verification script for semantic search.
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
from v3.models.deck import CardSearchFilters

def verify_semantic_search():
    print("Initializing services...")
    db_service = DatabaseService("v3/data/cards.db")
    vector_service = VectorService("v3/data/chroma_db")
    card_repo = CardRepository(db_service, vector_service=vector_service)
    
    queries = [
        "aggressive red creature",
        "blue counterspell",
        "removal that exiles",
        "creature that gives life"
    ]
    
    print("\n--- Testing Semantic Search ---")
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = card_repo.semantic_search(query, limit=3)
        for card in results:
            print(f"- {card.name} ({card.type_line}): {card.oracle_text[:50]}...")

if __name__ == "__main__":
    verify_semantic_search()
