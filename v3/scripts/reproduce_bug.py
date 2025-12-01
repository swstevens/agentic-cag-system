"""
Reproduction script for deck builder bugs.
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.services.agent_deck_builder_service import AgentDeckBuilderService
from v3.models.deck import Deck, DeckCard, MTGCard
from v3.database.card_repository import CardRepository
from v3.database.database_service import DatabaseService

def test_remove_card_logic():
    print("Testing _remove_card logic...")
    
    # Mock service (we only need the method)
    service = AgentDeckBuilderService(CardRepository(DatabaseService()))
    
    # Create a dummy deck
    card = MTGCard(id="mountain", name="Mountain", type_line="Basic Land", cmc=0.0)
    deck = Deck(
        cards=[DeckCard(card=card, quantity=10)],
        format="Standard",
        archetype="Aggro"
    )
    deck.calculate_totals()
    print(f"Initial deck: {deck.total_cards} cards")
    
    # Try to remove 5 mountains
    print("Removing 5 Mountains...")
    service._remove_card(deck, "Mountain", 5)
    deck.calculate_totals()
    print(f"After removal: {deck.total_cards} cards")
    
    if deck.total_cards != 5:
        print("FAIL: Expected 5 cards, got", deck.total_cards)
    else:
        print("PASS: Removal logic works (surprisingly?)")

if __name__ == "__main__":
    test_remove_card_logic()
