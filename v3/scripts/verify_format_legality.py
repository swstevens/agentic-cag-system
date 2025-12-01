"""
Script to verify format legality of cards in a deck.
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v3.database.database_service import DatabaseService
from v3.database.card_repository import CardRepository

# Cards from the final deck
cards = [
    "Fanatical Firebrand",
    "Flamewake Phoenix",
    "Brazen Scourge",
    "Courageous Goblin",
    "Devoted Duelist",
    "Dropkick Bomber",
    "Dragon Fodder",
    "Fire Magic",
    "Felonious Rage",
    "Enterprising Scallywag",
    "Blazing Bomb",
    "Burnout Bashtronaut",
    "Clockwork Percussionist",
    "Dragonmaster Outcast",
    "Dynamite Diver",
    "Embereth Veteran",
]

db = DatabaseService('v3/data/cards.db')
repo = CardRepository(db)

print("Checking Standard legality of deck cards:\n")
illegal_cards = []

for card_name in cards:
    card = repo.get_by_name(card_name)
    if card:
        standard_legal = card.legalities.get("standard", "Not Legal")
        status = "✓" if standard_legal == "Legal" else "✗"
        print(f"{status} {card_name}: {standard_legal}")
        if standard_legal != "Legal":
            illegal_cards.append(card_name)
    else:
        print(f"✗ {card_name}: NOT FOUND IN DB")
        illegal_cards.append(card_name)

print(f"\n{'='*60}")
if illegal_cards:
    print(f"❌ Found {len(illegal_cards)} illegal cards:")
    for card in illegal_cards:
        print(f"  - {card}")
else:
    print("✅ All cards are Standard-legal!")
