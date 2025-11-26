"""
Script to import card data from v2 database to v3 SQLite database.

This is a one-time migration script to populate the v3 database
with card data from the v2 system.
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from v3.database.database_service import DatabaseService


def import_from_v2_json(json_path: str, db_service: DatabaseService) -> int:
    """
    Import cards from v2 JSON file.
    
    Args:
        json_path: Path to AtomicCards.json or similar
        db_service: Database service instance
        
    Returns:
        Number of cards imported
    """
    print(f"Loading cards from {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if 'data' in data:
        # MTGJSON format
        cards_dict = data['data']
        cards = []
        for card_name, card_versions in cards_dict.items():
            # Take first version of each card
            if isinstance(card_versions, list) and len(card_versions) > 0:
                cards.append(card_versions[0])
            elif isinstance(card_versions, dict):
                cards.append(card_versions)
    else:
        # Assume it's a list of cards
        cards = data if isinstance(data, list) else []
    
    print(f"Found {len(cards)} cards to import")
    
    # Convert to v3 format and insert
    converted_cards = []
    for card in cards:
        try:
            converted = {
                'id': card.get('uuid', card.get('id', card.get('name', '').lower().replace(' ', '_'))),
                'name': card.get('name', ''),
                'mana_cost': card.get('manaCost', card.get('mana_cost')),
                'cmc': float(card.get('manaValue', card.get('cmc', 0))),
                'colors': card.get('colors', []),
                'color_identity': card.get('colorIdentity', card.get('color_identity', [])),
                'type_line': card.get('type', card.get('type_line', '')),
                'types': card.get('types', []),
                'subtypes': card.get('subtypes', []),
                'oracle_text': card.get('text', card.get('oracle_text')),
                'power': card.get('power'),
                'toughness': card.get('toughness'),
                'loyalty': card.get('loyalty'),
                'set_code': card.get('setCode', card.get('set_code', '')),
                'rarity': card.get('rarity', ''),
                'legalities': card.get('legalities', {}),
                'keywords': card.get('keywords', []),
            }
            converted_cards.append(converted)
        except Exception as e:
            print(f"Error converting card {card.get('name', 'unknown')}: {e}")
            continue
    
    print(f"Importing {len(converted_cards)} cards...")
    count = db_service.bulk_insert_cards(converted_cards)
    print(f"Successfully imported {count} cards")
    
    return count


def create_sample_cards(db_service: DatabaseService) -> int:
    """
    Create sample cards for testing when no v2 data is available.
    
    Args:
        db_service: Database service instance
        
    Returns:
        Number of cards created
    """
    sample_cards = [
        # Red Aggro Cards
        {
            'id': 'goblin_guide',
            'name': 'Goblin Guide',
            'mana_cost': '{R}',
            'cmc': 1.0,
            'colors': ['R'],
            'color_identity': ['R'],
            'type_line': 'Creature — Goblin Scout',
            'types': ['Creature'],
            'subtypes': ['Goblin', 'Scout'],
            'oracle_text': 'Haste\nWhenever Goblin Guide attacks, defending player reveals the top card of their library.',
            'power': '2',
            'toughness': '2',
            'rarity': 'Rare',
            'legalities': {'Standard': 'Legal', 'Modern': 'Legal'},
            'keywords': ['Haste'],
        },
        {
            'id': 'lightning_bolt',
            'name': 'Lightning Bolt',
            'mana_cost': '{R}',
            'cmc': 1.0,
            'colors': ['R'],
            'color_identity': ['R'],
            'type_line': 'Instant',
            'types': ['Instant'],
            'oracle_text': 'Lightning Bolt deals 3 damage to any target.',
            'rarity': 'Common',
            'legalities': {'Standard': 'Legal', 'Modern': 'Legal'},
            'keywords': [],
        },
        {
            'id': 'monastery_swiftspear',
            'name': 'Monastery Swiftspear',
            'mana_cost': '{R}',
            'cmc': 1.0,
            'colors': ['R'],
            'color_identity': ['R'],
            'type_line': 'Creature — Human Monk',
            'types': ['Creature'],
            'subtypes': ['Human', 'Monk'],
            'oracle_text': 'Haste\nProwess',
            'power': '1',
            'toughness': '2',
            'rarity': 'Uncommon',
            'legalities': {'Standard': 'Legal', 'Modern': 'Legal'},
            'keywords': ['Haste', 'Prowess'],
        },
        {
            'id': 'mountain',
            'name': 'Mountain',
            'type_line': 'Basic Land — Mountain',
            'types': ['Land'],
            'subtypes': ['Mountain'],
            'oracle_text': 'Tap: Add {R}.',
            'rarity': 'Common',
            'legalities': {'Standard': 'Legal', 'Modern': 'Legal'},
            'keywords': [],
        },
    ]
    
    print(f"Creating {len(sample_cards)} sample cards...")
    count = db_service.bulk_insert_cards(sample_cards)
    print(f"Successfully created {count} sample cards")
    
    return count


def main():
    """Main import function."""
    db_service = DatabaseService()
    
    # Check if v2 data exists
    v2_json_path = 'v2/data/AtomicCards.json'
    
    if os.path.exists(v2_json_path):
        print("Found v2 data, importing...")
        count = import_from_v2_json(v2_json_path, db_service)
    else:
        print("No v2 data found, creating sample cards for testing...")
        count = create_sample_cards(db_service)
    
    # Display stats
    total_cards = db_service.get_card_count()
    print(f"\nDatabase now contains {total_cards} cards")


if __name__ == '__main__':
    main()
