"""Debug script to test database initialization."""
import sqlite3

# Test 1: Direct connection
print("=== Test 1: Direct Connection ===")
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
conn.commit()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables after direct create: {tables}")
conn.close()

# Test 2: Using DatabaseService
print("\n=== Test 2: Using DatabaseService ===")
from v3.database.database_service import DatabaseService

print("Creating DatabaseService...")
db = DatabaseService(db_path=":memory:")
print("DatabaseService created")

# Check if tables exist
print("Checking tables...")
with db.get_connection() as conn:
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print(f"Tables in database: {[t[0] for t in tables]}")

    # Check if decks table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='decks';")
    decks_table = cursor.fetchone()

    if decks_table:
        print("✓ Decks table exists!")

        # Get schema
        cursor.execute("PRAGMA table_info(decks);")
        columns = cursor.fetchall()
        print("\nDecks table schema:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    else:
        print("✗ Decks table does NOT exist!")
