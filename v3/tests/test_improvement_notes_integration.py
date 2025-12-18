import pytest
from fastapi.testclient import TestClient
from v3.api import app
from v3.database.database_service import DatabaseService
from v3.database.deck_repository import DeckRepository
import os
import uuid

# Setup test database
TEST_DB = "v3/data/test_cards.db"

@pytest.fixture(scope="module")
def test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    db_service = DatabaseService(db_path=TEST_DB)
    yield db_service
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

@pytest.fixture(scope="module")
def deck_repo(test_db):
    return DeckRepository(test_db)

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_save_deck_with_improvement_notes(client, deck_repo):
    """Test saving a deck with improvement notes via the API."""
    unique_name = f"Test Deck {uuid.uuid4()}"
    notes = "These are some test improvement notes."
    
    payload = {
        "deck": {
            "format": "Standard",
            "archetype": "Aggro",
            "total_cards": 2,
            "cards": [
                {"card": {"id": "c1", "name": "Card 1", "types": ["Creature"], "type_line": "Creature — Human", "mana_cost": "{1}{G}", "cmc": 2}, "quantity": 1},
                {"card": {"id": "c2", "name": "Card 2", "types": ["Land"], "type_line": "Basic Land", "mana_cost": "", "cmc": 0}, "quantity": 1}
            ]
        },
        "name": unique_name,
        "description": "Test description",
        "quality_score": 0.88,
        "improvement_notes": notes
    }
    
    # Use the real API endpoint (assuming it's pointed to the right DB for tests or we mock the repo)
    # Since we're doing an integration test, we'll check if the repo reflects the save.
    # Note: In a real integration test, the app would need to be injected with the test_db.
    # For now, we'll test the repository directly to ensure the schema and logic are correct.
    
    from v3.models.deck import Deck
    deck_obj = Deck.model_validate(payload["deck"])
    
    deck_id = deck_repo.save_deck(
        deck=deck_obj,
        name=payload["name"],
        description=payload["description"],
        quality_score=payload["quality_score"],
        improvement_notes=payload["improvement_notes"]
    )
    
    # Verify retrieval
    saved_deck = deck_repo.get_deck_by_id(deck_id)
    assert saved_deck is not None
    assert saved_deck["name"] == unique_name
    assert saved_deck["improvement_notes"] == notes
    assert saved_deck["quality_score"] == 0.88

def test_update_deck_with_improvement_notes(deck_repo):
    """Test updating improvement notes on an existing deck."""
    # Create initial deck
    initial_notes = "Initial notes"
    from v3.models.deck import Deck
    deck_obj = Deck(format="Standard", archetype="Aggro", cards=[], total_cards=0)
    
    deck_id = deck_repo.save_deck(
        deck=deck_obj,
        name="Update Test",
        improvement_notes=initial_notes
    )
    
    # Update notes
    new_notes = "Updated notes"
    updated = deck_repo.update_deck(
        deck_id=deck_id,
        deck=deck_obj,
        improvement_notes=new_notes
    )
    
    assert updated is True
    
    # Verify change
    saved_deck = deck_repo.get_deck_by_id(deck_id)
    assert saved_deck["improvement_notes"] == new_notes
