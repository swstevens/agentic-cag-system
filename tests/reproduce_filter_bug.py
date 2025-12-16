import sys
import os
import json
import uuid

# Add the project root to sys.path
sys.path.append(os.getcwd())

from v3.database.database_service import DatabaseService
from v3.database.deck_repository import DeckRepository
from v3.models.deck import Deck

def reproduce():
    # Use a temporary database for testing
    db_path = "tests/test_decks.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db_service = DatabaseService(db_path=db_path)
    repo = DeckRepository(db_service)
    
    # Create a test deck
    deck_data = {
        "format": "Standard",
        "archetype": "Aggro",
        "colors": ["R"],
        "total_cards": 60,
        "cards": [],
        "sideboard": []
    }
    deck = Deck(**deck_data)
    
    deck_id = repo.save_deck(deck, "Test Deck", "A test deck", 0.8)
    print(f"Saved deck with ID: {deck_id}")
    
    # Test retrieving without filters
    all_decks = repo.list_decks()
    print(f"All decks count: {len(all_decks)}")
    
    # Test retrieving with format filter (Standard)
    standard_decks = repo.list_decks(format_filter="Standard")
    print(f"Standard decks count: {len(standard_decks)}")
    
    # Test retrieving with format filter (lowercase)
    standard_lower_decks = repo.list_decks(format_filter="standard")
    print(f"Standard (lower) decks count: {len(standard_lower_decks)}")
    
    # Test retrieving with archetype filter (Aggro)
    aggro_decks = repo.list_decks(archetype_filter="Aggro")
    print(f"Aggro decks count: {len(aggro_decks)}")
    
    # Test retrieving with bugged format filter (All Formats)
    all_formats_decks = repo.list_decks(format_filter="All Formats")
    print(f"All Formats decks count: {len(all_formats_decks)}")

    # Test retrieving with both filters
    both_decks = repo.list_decks(format_filter="Standard", archetype_filter="Aggro")
    print(f"Both filters decks count: {len(both_decks)}")

if __name__ == "__main__":
    reproduce()
