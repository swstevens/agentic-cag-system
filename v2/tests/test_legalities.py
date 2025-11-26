"""Quick test script to verify legality filtering"""
import sys
sys.path.insert(0, '/home/shea/Documents/GitHub/agentic-cag-system')

from mtg_cag_system.services.database_service import DatabaseService

# Initialize database
db = DatabaseService(db_path="./data/cards.db")
db.connect()

# Test 1: Search for cards legal in Standard
print("=" * 80)
print("TEST 1: Searching for cards legal in Standard (with Forest in the mix)")
print("=" * 80)
cards = db.search_cards(
    query="Forest",
    format_legality={"standard": "legal"},
    limit=5
)

print(f"\nFound {len(cards)} cards legal in Standard with 'Forest' in text/name:")
for card in cards[:3]:
    std_status = card.legalities.get('standard', 'not_found')
    print(f"  - {card.name}: Standard={std_status}")
    print(f"    Legalities: {card.legalities}")

# Test 2: Search for green cards legal in Standard
print("\n" + "=" * 80)
print("TEST 2: Searching for green cards legal in Standard")
print("=" * 80)
cards = db.search_cards(
    colors=["G"],
    format_legality={"standard": "legal"},
    limit=10
)

print(f"\nFound {len(cards)} green cards legal in Standard:")
for card in cards[:5]:
    std_status = card.legalities.get('standard', 'not_found')
    print(f"  - {card.name}: Standard={std_status}, Colors={card.colors}")

# Test 3: Verify that cards without legalities are filtered out
print("\n" + "=" * 80)
print("TEST 3: Verify all returned cards have Standard='Legal'")
print("=" * 80)
all_legal = all(card.legalities.get('standard', '').lower() == 'legal' for card in cards)
print(f"All cards have Standard='Legal': {all_legal}")

if not all_legal:
    print("\nCards with non-Legal status:")
    for card in cards:
        status = card.legalities.get('standard', 'missing')
        if status.lower() != 'legal':
            print(f"  - {card.name}: {status}")

db.disconnect()
print("\n✅ Tests complete!")
