#!/usr/bin/env python3
"""
Load AtomicCards.json into SQLite database

AtomicCards.json contains unique cards (one per oracle text) without set-specific data.
This gives us ~26K unique cards instead of 107K printings.
"""

import json
import sqlite3
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_schema(conn: sqlite3.Connection):
    """Create database schema for atomic cards"""
    cursor = conn.cursor()

    # Main cards table - simplified for AtomicCards (no set-specific data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            uuid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mana_cost TEXT,
            cmc REAL DEFAULT 0,
            colors TEXT,
            color_identity TEXT,
            type_line TEXT,
            types TEXT,
            subtypes TEXT,
            supertypes TEXT,
            oracle_text TEXT,
            power TEXT,
            toughness TEXT,
            loyalty TEXT,
            keywords TEXT,
            layout TEXT,
            first_printing TEXT
        )
    """)

    # Legalities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cardLegalities (
            uuid TEXT PRIMARY KEY,
            alchemy TEXT,
            brawl TEXT,
            commander TEXT,
            duel TEXT,
            future TEXT,
            gladiator TEXT,
            historic TEXT,
            legacy TEXT,
            modern TEXT,
            oathbreaker TEXT,
            oldschool TEXT,
            pauper TEXT,
            paupercommander TEXT,
            penny TEXT,
            pioneer TEXT,
            predh TEXT,
            premodern TEXT,
            standard TEXT,
            standardbrawl TEXT,
            timeless TEXT,
            vintage TEXT,
            FOREIGN KEY (uuid) REFERENCES cards(uuid)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_types ON cards(types)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_colors ON cards(color_identity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cards_cmc ON cards(cmc)")

    # FTS5 virtual table for full-text search
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
            name,
            oracle_text,
            type_line,
            content=cards,
            content_rowid=rowid
        )
    """)

    conn.commit()
    print("✅ Database schema created")


def parse_atomic_card(card_name: str, card_data: Dict[str, Any]) -> tuple:
    """
    Parse a card from AtomicCards.json format

    Returns:
        (card_row, legalities_row) tuples for insertion
    """
    # Generate UUID from Scryfall Oracle ID or name
    uuid = card_data.get('identifiers', {}).get('scryfallOracleId', card_name)

    # Convert lists to comma-separated strings for SQLite
    colors = ','.join(card_data.get('colors', []))
    color_identity = ','.join(card_data.get('colorIdentity', []))
    types = ','.join(card_data.get('types', []))
    subtypes = ','.join(card_data.get('subtypes', []))
    supertypes = ','.join(card_data.get('supertypes', []))
    keywords = ','.join(card_data.get('keywords', []))

    # Card row
    card_row = (
        uuid,
        card_name,
        card_data.get('manaCost'),
        card_data.get('manaValue', 0.0),
        colors,
        color_identity,
        card_data.get('type'),  # AtomicCards uses 'type' not 'type_line'
        types,
        subtypes,
        supertypes,
        card_data.get('text'),  # AtomicCards uses 'text' not 'oracle_text'
        card_data.get('power'),
        card_data.get('toughness'),
        card_data.get('loyalty'),
        keywords,
        card_data.get('layout'),
        card_data.get('firstPrinting')
    )

    # Legalities row
    legalities = card_data.get('legalities', {})
    legalities_row = (
        uuid,
        legalities.get('alchemy'),
        legalities.get('brawl'),
        legalities.get('commander'),
        legalities.get('duel'),
        legalities.get('future'),
        legalities.get('gladiator'),
        legalities.get('historic'),
        legalities.get('legacy'),
        legalities.get('modern'),
        legalities.get('oathbreaker'),
        legalities.get('oldschool'),
        legalities.get('pauper'),
        legalities.get('paupercommander'),
        legalities.get('penny'),
        legalities.get('pioneer'),
        legalities.get('predh'),
        legalities.get('premodern'),
        legalities.get('standard'),
        legalities.get('standardbrawl'),
        legalities.get('timeless'),
        legalities.get('vintage')
    )

    return card_row, legalities_row


def load_atomic_cards(json_path: str, db_path: str):
    """Load AtomicCards.json into SQLite database"""
    print(f"Loading cards from {json_path}...")

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract card data
    card_data = data.get('data', {})
    total_cards = len(card_data)
    print(f"Found {total_cards:,} unique cards")

    # Connect to database
    conn = sqlite3.connect(db_path)
    create_schema(conn)
    cursor = conn.cursor()

    # Insert cards
    inserted = 0
    skipped = 0

    for card_name, versions in card_data.items():
        # AtomicCards usually has one version per card, but handle array anyway
        for version in versions:
            try:
                card_row, legalities_row = parse_atomic_card(card_name, version)

                # Insert card
                cursor.execute("""
                    INSERT OR REPLACE INTO cards VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, card_row)

                # Insert legalities (if any exist)
                if any(legalities_row[1:]):  # Check if any legality is not None
                    cursor.execute("""
                        INSERT OR REPLACE INTO cardLegalities VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, legalities_row)

                inserted += 1

                # Commit in batches
                if inserted % 1000 == 0:
                    conn.commit()
                    print(f"Inserted {inserted:,}/{total_cards:,} cards...", end='\r')

            except Exception as e:
                print(f"\nError inserting {card_name}: {e}")
                skipped += 1
                continue

    # Final commit
    conn.commit()

    # Rebuild FTS index
    print("\n\nRebuilding full-text search index...")
    cursor.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")
    conn.commit()

    # Get final counts
    card_count = cursor.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    legalities_count = cursor.execute("SELECT COUNT(*) FROM cardLegalities").fetchone()[0]

    conn.close()

    print("\n" + "=" * 80)
    print("✅ IMPORT COMPLETE")
    print("=" * 80)
    print(f"Total unique cards: {card_count:,}")
    print(f"Cards with legalities: {legalities_count:,}")
    print(f"Skipped: {skipped}")
    print(f"Database: {db_path}")
    print()


if __name__ == "__main__":
    json_path = "./data/AtomicCards.json"
    db_path = "./data/cards_atomic.db"

    load_atomic_cards(json_path, db_path)
