import sqlite3
import os

db_path = "v3/data/cards.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("SELECT count(*) FROM cards")
    print(f"Total cards: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT count(*) FROM cards WHERE legalities LIKE '%Standard%'")
    print(f"Standard legal cards: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT name, legalities FROM cards LIMIT 5")
    print("Sample cards:")
    for row in cursor.fetchall():
        print(row)
        
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
