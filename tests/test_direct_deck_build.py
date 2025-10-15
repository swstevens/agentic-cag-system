"""
Direct Deck Builder Test

Builds a deck by directly querying the database for Modern-legal red cards
"""

import asyncio
import os
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.agents.symbolic_reasoning_agent import SymbolicReasoningAgent

async def build_simple_deck():
    print("=" * 80)
    print("DIRECT DECK BUILD: Modern Mono-Red Aggro")
    print("=" * 80)
    
    # Setup
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"
    
    db = DatabaseService(db_path)
    db.connect()
    
    card_lookup = CardLookupService(database_service=db, cache_size=200)
    
    # Create symbolic agent for validation
    api_key = os.getenv("OPENAI_API_KEY")
    symbolic_agent = SymbolicReasoningAgent(
        model_name="openai:gpt-4o-mini",
        api_key=api_key
    )
    
    #Define a specific decklist
    deck_plan = [
        ("Monastery Swiftspear", 4),
        ("Soul-Scar Mage", 4),
        ("Goblin Guide", 4),
        ("Eidolon of the Great Revel", 4),
        ("Lightning Bolt", 4),
        ("Lava Spike", 4),
        ("Rift Bolt", 4),
        ("Skewer the Critics", 4),
        ("Light Up the Stage", 4),
        ("Mountain", 24)
    ]
    
    # Build deck
    deck = []
    print("\nBuilding deck...")
    
    for card_name, count in deck_plan:
        card = card_lookup.get_card(card_name)
        if card:
            for _ in range(count):
                deck.append(card.model_dump())
            print(f"  ✓ {count}x {card_name}")
        else:
            print(f"  ✗ Card not found: {card_name}")
    
    print(f"\nTotal cards: {len(deck)}")
    
    # Validate
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    validation_response = await symbolic_agent.process({
        'type': 'deck_validation',
        'data': {
            'cards': deck,
            'format': 'Modern'
        }
    })
    
    val = validation_response.data
    print(f"\nValid: {val['valid']}")
    print(f"Validations:")
    for key, value in val['validations'].items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")
    
    db.disconnect()
    
    if val['valid']:
        print("\n" + "=" * 80)
        print("✅ DECK IS LEGAL AND READY TO PLAY!")
        print("=" * 80)
    
    return deck, val

if __name__ == "__main__":
    asyncio.run(build_simple_deck())
