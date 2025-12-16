
import sys
import os
import sqlite3
import json

# Add the project root to sys.path
sys.path.append(os.getcwd())

def inspect_db():
    db_path = "v3/data/cards.db"
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check decks table schema
    cursor.execute("PRAGMA table_info(decks)")
    columns = cursor.fetchall()
    print("Decks Table Schema:")
    for col in columns:
        print(dict(col))
    
    # Check decks content
    cursor.execute("SELECT id, name, format, archetype FROM decks")
    rows = cursor.fetchall()
    print(f"\nTotal Decks: {len(rows)}")
    for row in rows:
        print(f"ID: {row['id']}, Name: {row['name']}, Format: '{row['format']}', Archetype: '{row['archetype']}'")

    if rows:
        # Test query for the first deck's format
        first_format = rows[0]['format']
        print(f"\nTesting query for format: '{first_format}'")
        cursor.execute("SELECT count(*) FROM decks WHERE LOWER(format) = LOWER(?)", (first_format,))
        count = cursor.fetchone()[0]
        print(f"Matches found: {count}")

    conn.close()

if __name__ == "__main__":
    inspect_db()
