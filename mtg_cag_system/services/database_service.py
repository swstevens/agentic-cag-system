import sqlite3
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from ..models.card import MTGCard, CardColor, CardType


class DatabaseService:
    """SQLite database service for MTG cards"""

    def __init__(self, db_path: str = "./data/cards.db"):
        # Public: Database path (users may need to access this)
        self.db_path = db_path

        # Private: Database connection (should not be accessed directly)
        self.__conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Connect to SQLite database (Public API)"""
        self.__conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.__conn.row_factory = sqlite3.Row  # Enable column access by name
        print(f"✅ Connected to database: {self.db_path}")

    def disconnect(self):
        """Disconnect from database (Public API)"""
        if self.__conn:
            self.__conn.close()
            print("Disconnected from database")

    def initialize_schema(self):
        """Create tables and indexes if they don't exist (Public API)"""
        if not self.__conn:
            raise RuntimeError("Database not connected")

        cursor = self.__conn.cursor()

        # Create cards table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                mana_cost TEXT,
                cmc REAL DEFAULT 0,
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

        # Create indexes for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON cards(name COLLATE NOCASE)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_set ON cards(set_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmc ON cards(cmc)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rarity ON cards(rarity)")

        # Create full-text search virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
                name,
                oracle_text,
                type_line,
                content=cards,
                content_rowid=rowid
            )
        """)

        self.__conn.commit()
        print("✅ Database schema initialized")

    def card_count(self) -> int:
        """Get total number of cards in database (Public API)"""
        if not self.__conn:
            return 0

        cursor = self.__conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cards")
        return cursor.fetchone()[0]

    def load_from_mtgjson(self, json_path: str, progress_callback=None):
        """
        Load cards from MTGJSON AllPrintings.json file (Public API)

        Args:
            json_path: Path to AllPrintings.json
            progress_callback: Optional function to call with progress updates
        """
        if not self.__conn:
            raise RuntimeError("Database not connected")

        print(f"📚 Loading cards from {json_path}...")

        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Extract the 'data' portion (MTGJSON v5 format has meta and data)
        if 'data' in json_data:
            data = json_data['data']
            print(f"   MTGJSON version: {json_data.get('meta', {}).get('version', 'unknown')}")
        else:
            # Fallback for older format
            data = json_data

        cursor = self.__conn.cursor()
        total_cards = 0
        inserted_cards = 0

        # Process each set
        for set_code, set_data in data.items():
            cards = set_data.get('cards', [])
            total_cards += len(cards)

            for card in cards:
                try:
                    # Convert card data to our schema
                    card_id = card.get('uuid', f"{set_code}_{card.get('name', 'unknown')}")

                    # Handle colors
                    colors = card.get('colors', [])
                    color_identity = card.get('colorIdentity', [])

                    # Handle types
                    types = card.get('types', [])
                    subtypes = card.get('subtypes', [])

                    # Handle legalities
                    legalities = card.get('legalities', {})

                    # Handle keywords
                    keywords = card.get('keywords', [])

                    cursor.execute("""
                        INSERT OR REPLACE INTO cards (
                            id, name, mana_cost, cmc, colors, color_identity,
                            type_line, types, subtypes, oracle_text,
                            power, toughness, loyalty, set_code, rarity,
                            legalities, keywords
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        card_id,
                        card.get('name'),
                        card.get('manaCost'),
                        card.get('manaValue', 0),  # MTGJSON uses 'manaValue' for CMC
                        json.dumps(colors),
                        json.dumps(color_identity),
                        card.get('type'),
                        json.dumps(types),
                        json.dumps(subtypes),
                        card.get('text'),  # MTGJSON uses 'text' for oracle text
                        card.get('power'),
                        card.get('toughness'),
                        card.get('loyalty'),
                        set_code,
                        card.get('rarity'),
                        json.dumps(legalities),
                        json.dumps(keywords)
                    ))

                    inserted_cards += 1

                    # Progress callback
                    if progress_callback and inserted_cards % 1000 == 0:
                        progress_callback(inserted_cards, total_cards)

                except Exception as e:
                    print(f"Error inserting card {card.get('name', 'unknown')}: {e}")
                    continue

        # Commit all inserts
        self.__conn.commit()

        # Rebuild FTS index
        print("🔄 Rebuilding full-text search index...")
        cursor.execute("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')")
        self.__conn.commit()

        print(f"✅ Loaded {inserted_cards} cards from {len(data)} sets")
        return inserted_cards

    def get_card_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Get a card by exact name (case-insensitive) (Public API)

        Args:
            name: Card name to search for

        Returns:
            MTGCard object or None if not found
        """
        if not self.__conn:
            return None

        cursor = self.__conn.cursor()
        cursor.execute(
            "SELECT * FROM cards WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (name,)
        )

        row = cursor.fetchone()
        if row:
            return self._row_to_card(row)
        return None

    def _normalize_color(self, color: str) -> str:
        """
        Convert color names to single-letter codes

        Args:
            color: Color name or code (e.g., "Red", "red", "R")

        Returns:
            Single-letter color code (W, U, B, R, G, C)
        """
        # Mapping of color names to codes
        color_map = {
            'white': 'W',
            'blue': 'U',
            'black': 'B',
            'red': 'R',
            'green': 'G',
            'colorless': 'C'
        }

        # Normalize input
        color_lower = color.lower().strip()

        # If it's already a single character code, return it uppercase
        if len(color) == 1:
            return color.upper()

        # Otherwise, look up in the map
        return color_map.get(color_lower, color.upper())

    def search_cards(
        self,
        query: Optional[str] = None,
        colors: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        cmc_min: Optional[float] = None,
        cmc_max: Optional[float] = None,
        rarity: Optional[str] = None,
        format_legality: Optional[Dict[str, str]] = None,  # e.g. {"standard": "legal"}
        strict_colors: bool = True,  # Only cards with EXACTLY these colors (no more, no less)
        limit: int = 100
    ) -> List[MTGCard]:
        """
        Search for cards with various filters (Public API)

        Args:
            query: Text to search in name/oracle text (uses FTS)
            colors: List of color codes or names (W/White, U/Blue, B/Black, R/Red, G/Green)
            types: List of types to filter by
            cmc_min: Minimum CMC
            cmc_max: Maximum CMC
            rarity: Card rarity
            format_legality: Format and status (e.g. {"standard": "legal"})
            strict_colors: If True, only return cards with EXACTLY these colors (mono-color decks)
                          If False, return cards that contain ANY of these colors (multicolor OK)
            limit: Maximum results to return

        Returns:
            List of matching MTGCard objects
        """
        if not self.__conn:
            return []

        cursor = self.__conn.cursor()

        # Build SQL query dynamically based on filters
        if query:
            # Use full-text search
            sql = """
                SELECT cards.* FROM cards
                JOIN cards_fts ON cards.rowid = cards_fts.rowid
                WHERE cards_fts MATCH ?
            """
            params = [query]
        else:
            sql = "SELECT * FROM cards WHERE 1=1"
            params = []

        # Add filters
        if colors:
            # Normalize color names to codes
            colors = [self._normalize_color(c) for c in colors]

            if strict_colors:
                # Strict mode for deck building:
                # - Mono-color: Only cards with EXACTLY that color or colorless
                # - Multi-color: Cards with ANY COMBINATION of the specified colors (but no other colors)
                #   Example: Golgari (BG) can have B, G, BG, or colorless - but NOT W, U, or R

                if len(colors) == 1:
                    # Mono-color: Match cards with exactly this color OR colorless
                    color = colors[0]
                    sql += " AND (color_identity LIKE ? OR color_identity = '[]')"
                    params.append(f'["{color}"]')
                else:
                    # Multi-color: Exclude cards that contain colors NOT in our list
                    # Get the opposite colors (colors we DON'T want)
                    all_colors = {'W', 'U', 'B', 'R', 'G'}
                    excluded_colors = all_colors - set(colors)

                    # Add exclusion conditions for each color we don't want
                    for excluded_color in excluded_colors:
                        sql += " AND color_identity NOT LIKE ?"
                        params.append(f'%"{excluded_color}"%')
            else:
                # Loose mode: Cards that contain ANY of the specified colors (multicolor OK)
                color_conditions = []
                for color in colors:
                    color_conditions.append("(colors LIKE ? OR color_identity LIKE ?)")
                    pattern = f'%"{color}"%'
                    params.extend([pattern, pattern])

                if color_conditions:
                    sql += " AND (" + " OR ".join(color_conditions) + ")"

        if types:
            for card_type in types:
                sql += " AND types LIKE ?"
                params.append(f'%"{card_type}"%')

        if cmc_min is not None:
            sql += " AND cmc >= ?"
            params.append(cmc_min)

        if cmc_max is not None:
            sql += " AND cmc <= ?"
            params.append(cmc_max)

        if rarity:
            sql += " AND rarity = ?"
            params.append(rarity)

        if format_legality:
            for format_name, status in format_legality.items():
                # Search in the raw JSON text since it's stored as a string
                # Legalities are stored as: {"format": "Status"} where format is lowercase
                # but Status has capital first letter (e.g., "Legal", "Banned", "Not_legal")
                sql += " AND legalities LIKE ?"
                # Capitalize the first letter of status to match the stored format
                status_capitalized = status.capitalize()
                # Match the exact JSON structure: {"format": "Legal"}
                params.append(f'%"{format_name.lower()}": "{status_capitalized}"%')

        sql += f" LIMIT {limit}"

        print("\nExecuting SQL Query:")
        print("SQL:", sql)
        print("Params:", params)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cards = [self._row_to_card(row) for row in rows]

        if colors and strict_colors:
            if len(colors) == 1:
                print(f"Found {len(cards)} mono-{colors[0]} cards (including colorless)")
            else:
                excluded = sorted(list({'W', 'U', 'B', 'R', 'G'} - set(colors)))
                print(f"Found {len(cards)} cards (excluding {', '.join(excluded)})")
        else:
            print(f"Found {len(cards)} cards")

        if len(cards) > 0:
            print("Sample cards:", ", ".join(c.name for c in cards[:5]))

        return cards

    def get_cards_by_format(self, format_name: str, status: str = "legal") -> List[MTGCard]:
        """
        Get all cards that have a specific legality status in a given format
        
        Args:
            format_name: The format to check (e.g. "standard", "modern", "commander")
            status: The legality status to look for (e.g. "legal", "not_legal", "banned")
            
        Returns:
            List of matching MTGCard objects
        """
        if not self.__conn:
            return []
            
        cursor = self.__conn.cursor()
        cursor.execute(
            "SELECT * FROM cards WHERE JSON_EXTRACT(legalities, ?) = ?",
            (f"$.{format_name.lower()}", status.lower())
        )
        
        rows = cursor.fetchall()
        return [self._row_to_card(row) for row in rows]

    def fuzzy_search(self, query: str, limit: int = 10) -> List[MTGCard]:
        """
        Fuzzy search for cards by name using LIKE (Public API)

        Args:
            query: Search term
            limit: Maximum results

        Returns:
            List of matching MTGCard objects
        """
        if not self.__conn:
            return []

        cursor = self.__conn.cursor()

        # Search with wildcards
        cursor.execute(
            "SELECT * FROM cards WHERE name LIKE ? LIMIT ?",
            (f"%{query}%", limit)
        )

        rows = cursor.fetchall()
        return [self._row_to_card(row) for row in rows]

    def _row_to_card(self, row: sqlite3.Row) -> MTGCard:
        """Convert SQLite row to MTGCard object (Protected - internal helper)"""
        # Parse JSON fields
        colors = json.loads(row['colors']) if row['colors'] else []
        color_identity = json.loads(row['color_identity']) if row['color_identity'] else []
        types = json.loads(row['types']) if row['types'] else []
        subtypes = json.loads(row['subtypes']) if row['subtypes'] else []
        legalities = json.loads(row['legalities']) if row['legalities'] else {}
        keywords = json.loads(row['keywords']) if row['keywords'] else []

        # Convert to CardColor enums
        try:
            color_enums = [CardColor(c) for c in colors if c in ['W', 'U', 'B', 'R', 'G', 'C']]
            color_identity_enums = [CardColor(c) for c in color_identity if c in ['W', 'U', 'B', 'R', 'G', 'C']]
        except:
            color_enums = []
            color_identity_enums = []

        # Convert to CardType enums
        try:
            type_enums = [CardType(t) for t in types if t in [e.value for e in CardType]]
        except:
            type_enums = []

        return MTGCard(
            id=row['id'],
            name=row['name'],
            mana_cost=row['mana_cost'],
            cmc=row['cmc'],
            colors=color_enums,
            color_identity=color_identity_enums,
            type_line=row['type_line'] or "",
            types=type_enums,
            subtypes=subtypes,
            oracle_text=row['oracle_text'],
            power=row['power'],
            toughness=row['toughness'],
            loyalty=row['loyalty'],
            set_code=row['set_code'],
            rarity=row['rarity'],
            legalities=legalities,
            keywords=keywords,
        )
