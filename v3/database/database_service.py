"""
SQLite3 Database Service for V3 Architecture.

Provides database connection management, schema creation,
and basic CRUD operations for MTG cards.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class DatabaseService:
    """
    SQLite3 database service for card storage and retrieval.
    
    Manages database connection, schema, and provides
    transaction support for card operations.
    """
    
    def __init__(self, db_path: str = "v3/data/cards.db"):
        """
        Initialize database service.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_schema()
    
    def _ensure_db_directory(self) -> None:
        """Ensure database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self) -> None:
        """Initialize database schema if not exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create cards table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    mana_cost TEXT,
                    cmc REAL,
                    colors TEXT,
                    color_identity TEXT,
                    type_line TEXT,
                    types TEXT,
                    subtypes TEXT,
                    oracle_text TEXT,
                    power TEXT,
                    toughness TEXT,
                    loyalty TEXT,
                    set_code TEXT,
                    rarity TEXT,
                    legalities TEXT,
                    keywords TEXT
                )
            """)
            
            # Create indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_name 
                ON cards(name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cmc 
                ON cards(cmc)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rarity
                ON cards(rarity)
            """)

            # Create saved_decks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS saved_decks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    deck_data TEXT NOT NULL,
                    category TEXT DEFAULT 'Uncategorized',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index on deck name for faster searches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_deck_name
                ON saved_decks(name)
            """)

            # Create index on category for filtering
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_deck_category
                ON saved_decks(category)
            """)

            conn.commit()
    
    def insert_card(self, card_data: Dict[str, Any]) -> None:
        """
        Insert a card into the database.
        
        Args:
            card_data: Dictionary containing card data
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert lists/dicts to JSON strings
            card_data = card_data.copy()
            for field in ['colors', 'color_identity', 'types', 'subtypes', 'legalities', 'keywords']:
                if field in card_data and card_data[field] is not None:
                    card_data[field] = json.dumps(card_data[field])
            
            cursor.execute("""
                INSERT OR REPLACE INTO cards (
                    id, name, mana_cost, cmc, colors, color_identity,
                    type_line, types, subtypes, oracle_text, power,
                    toughness, loyalty, set_code, rarity, legalities, keywords
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_data.get('id'),
                card_data.get('name'),
                card_data.get('mana_cost'),
                card_data.get('cmc', 0.0),
                card_data.get('colors'),
                card_data.get('color_identity'),
                card_data.get('type_line'),
                card_data.get('types'),
                card_data.get('subtypes'),
                card_data.get('oracle_text'),
                card_data.get('power'),
                card_data.get('toughness'),
                card_data.get('loyalty'),
                card_data.get('set_code'),
                card_data.get('rarity'),
                card_data.get('legalities'),
                card_data.get('keywords'),
            ))
    
    def get_card_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a card by exact name.
        
        Args:
            name: Card name (case-insensitive)
            
        Returns:
            Card data dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM cards WHERE LOWER(name) = LOWER(?)",
                (name,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def get_card_by_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a card by ID.
        
        Args:
            card_id: Unique card identifier
            
        Returns:
            Card data dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def search_cards(
        self,
        colors: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        cmc_min: Optional[float] = None,
        cmc_max: Optional[float] = None,
        rarity: Optional[str] = None,
        format_legal: Optional[str] = None,
        text_query: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for cards matching criteria.
        
        Args:
            colors: List of color codes (W, U, B, R, G)
            types: List of card types
            cmc_min: Minimum converted mana cost
            cmc_max: Maximum converted mana cost
            rarity: Card rarity
            format_legal: Format name (e.g., "Standard", "Modern")
            text_query: Text to search in oracle text
            limit: Maximum results to return
            
        Returns:
            List of card data dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM cards WHERE 1=1"
            params = []
            
            if cmc_min is not None:
                query += " AND cmc >= ?"
                params.append(cmc_min)
            
            if cmc_max is not None:
                query += " AND cmc <= ?"
                params.append(cmc_max)
            
            if rarity:
                query += " AND LOWER(rarity) = LOWER(?)"
                params.append(rarity)
            
            if format_legal:
            # Add SQL filtering for format legality to ensure we get relevant cards
            # Legalities are stored as JSON: {"standard": "Legal", ...}
                query += " AND LOWER(legalities) LIKE ?"
                params.append(f'%"{format_legal.lower()}": "legal"%')
        
            if colors:
            # Add SQL filtering for colors
            # Colors are stored as JSON list: ["R", "G"]
            # We want to find cards that have at least one of the requested colors
            # This is a loose filter, strict checking happens in Python
                color_conditions = []
                for color in colors:
                    color_conditions.append("colors LIKE ?")
                    params.append(f'%"{color}"%')
                
                if color_conditions:
                    query += f" AND ({' OR '.join(color_conditions)})"

            if text_query:
                query += " AND LOWER(oracle_text) LIKE LOWER(?)"
                params.append(f"%{text_query}%")
        
            # Note: Color and type filtering requires JSON parsing
            # We do post-filtering in Python for these fields
            
            query += f" LIMIT ?"
            params.append(limit * 2)  # Fetch 2x for post-filtering (colors/types)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = [self._row_to_dict(row) for row in rows]
            
            # Post-filter for colors and types (SQL can't efficiently query JSON arrays)
            if colors:
                results = [
                    card for card in results
                    if any(color in card.get('colors', []) for color in colors)
                ]
            
            if types:
                results = [
                    card for card in results
                    if any(card_type in card.get('types', []) for card_type in types)
                ]
            
            # Format legality already filtered in SQL, no need to re-filter here
            
            return results[:limit]
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert database row to dictionary with JSON parsing.
        
        Args:
            row: SQLite row object
            
        Returns:
            Dictionary with parsed JSON fields
        """
        data = dict(row)
        
        # Parse JSON fields
        for field in ['colors', 'color_identity', 'types', 'subtypes', 'legalities', 'keywords']:
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    data[field] = []
        
        return data
    
    def bulk_insert_cards(self, cards: List[Dict[str, Any]]) -> int:
        """
        Insert multiple cards in a single transaction.
        
        Args:
            cards: List of card data dictionaries
            
        Returns:
            Number of cards inserted
        """
        count = 0
        with self.get_connection() as conn:
            for card_data in cards:
                try:
                    cursor = conn.cursor()
                    
                    # Convert lists/dicts to JSON strings
                    card_data = card_data.copy()
                    for field in ['colors', 'color_identity', 'types', 'subtypes', 'legalities', 'keywords']:
                        if field in card_data and card_data[field] is not None:
                            card_data[field] = json.dumps(card_data[field])
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO cards (
                            id, name, mana_cost, cmc, colors, color_identity,
                            type_line, types, subtypes, oracle_text, power,
                            toughness, loyalty, set_code, rarity, legalities, keywords
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        card_data.get('id'),
                        card_data.get('name'),
                        card_data.get('mana_cost'),
                        card_data.get('cmc', 0.0),
                        card_data.get('colors'),
                        card_data.get('color_identity'),
                        card_data.get('type_line'),
                        card_data.get('types'),
                        card_data.get('subtypes'),
                        card_data.get('oracle_text'),
                        card_data.get('power'),
                        card_data.get('toughness'),
                        card_data.get('loyalty'),
                        card_data.get('set_code'),
                        card_data.get('rarity'),
                        card_data.get('legalities'),
                        card_data.get('keywords'),
                    ))
                    count += 1
                except Exception as e:
                    print(f"Error inserting card {card_data.get('name', 'unknown')}: {e}")
                    continue
        
        return count
    
    def get_card_count(self) -> int:
        """
        Get total number of cards in database.

        Returns:
            Card count
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cards")
            return cursor.fetchone()[0]

    # Saved Decks CRUD Operations

    def create_saved_deck(self, name: str, deck_data: Dict[str, Any], category: str = "Uncategorized") -> int:
        """
        Save a deck to the database.

        Args:
            name: Deck name
            deck_data: Dictionary containing deck data (will be serialized to JSON)
            category: Deck category

        Returns:
            ID of the created deck
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO saved_decks (name, deck_data, category)
                VALUES (?, ?, ?)
            """, (name, json.dumps(deck_data), category))
            return cursor.lastrowid

    def get_saved_deck(self, deck_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a saved deck by ID.

        Args:
            deck_id: Deck ID

        Returns:
            Deck dictionary or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_decks WHERE id = ?", (deck_id,))
            row = cursor.fetchone()

            if row:
                return self._deck_row_to_dict(row)
            return None

    def get_all_saved_decks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all saved decks, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of deck dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if category:
                cursor.execute(
                    "SELECT * FROM saved_decks WHERE category = ? ORDER BY updated_at DESC",
                    (category,)
                )
            else:
                cursor.execute("SELECT * FROM saved_decks ORDER BY updated_at DESC")

            rows = cursor.fetchall()
            return [self._deck_row_to_dict(row) for row in rows]

    def update_saved_deck(
        self,
        deck_id: int,
        name: Optional[str] = None,
        deck_data: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Update a saved deck.

        Args:
            deck_id: Deck ID
            name: New deck name (optional)
            deck_data: New deck data (optional)
            category: New category (optional)

        Returns:
            True if updated, False if deck not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build dynamic update query
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)

            if deck_data is not None:
                updates.append("deck_data = ?")
                params.append(json.dumps(deck_data))

            if category is not None:
                updates.append("category = ?")
                params.append(category)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(deck_id)

            query = f"UPDATE saved_decks SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            return cursor.rowcount > 0

    def delete_saved_deck(self, deck_id: int) -> bool:
        """
        Delete a saved deck.

        Args:
            deck_id: Deck ID

        Returns:
            True if deleted, False if deck not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_decks WHERE id = ?", (deck_id,))
            return cursor.rowcount > 0

    def _deck_row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert saved deck row to dictionary.

        Args:
            row: SQLite row object

        Returns:
            Dictionary with parsed deck data
        """
        data = dict(row)

        # Parse deck_data JSON
        if data.get('deck_data'):
            try:
                data['deck_data'] = json.loads(data['deck_data'])
            except (json.JSONDecodeError, TypeError):
                data['deck_data'] = {}

        return data
