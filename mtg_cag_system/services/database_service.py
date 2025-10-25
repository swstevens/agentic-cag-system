"""SQLAlchemy-based database service for MTG cards"""
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy import create_engine, select, func, or_, and_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from ..models.card import MTGCard, CardColor, CardType
from ..models.card_orm import CardORM, Base
from ..models.converters import orm_to_pydantic, pydantic_to_orm, orm_list_to_pydantic

logger = logging.getLogger(__name__)


class DatabaseService:
    """SQLAlchemy database service for MTG cards - API-compatible with old version"""

    def __init__(self, db_path: str = "./data/cards.db"):
        # Public: Database path
        self.db_path = db_path

        # Private: SQLAlchemy engine and session
        self.__engine = None
        self.__SessionLocal = None
        self.__session: Optional[Session] = None

    def connect(self):
        """Connect to SQLite database using SQLAlchemy"""
        # Create engine
        database_url = f"sqlite:///{self.db_path}"
        self.__engine = create_engine(
            database_url,
            echo=False,  # Set to True for SQL debug logging
            connect_args={"check_same_thread": False}  # Allow multi-threaded access
        )

        # Create session factory
        self.__SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.__engine
        )

        # Create a session
        self.__session = self.__SessionLocal()
        logger.info(f"Connected to database: {self.db_path}")

    def disconnect(self):
        """Disconnect from database"""
        if self.__session:
            self.__session.close()
            self.__session = None
        if self.__engine:
            self.__engine.dispose()
            self.__engine = None
        logger.info("Disconnected from database")

    def initialize_schema(self):
        """Create tables and indexes if they don't exist"""
        if not self.__engine:
            raise RuntimeError("Database not connected")

        # Create all tables defined in Base metadata
        Base.metadata.create_all(self.__engine)

        # Create FTS5 virtual table (still using raw SQL as SQLAlchemy doesn't support FTS5)
        with self.__engine.connect() as conn:
            conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
                    name,
                    oracle_text,
                    type_line,
                    content=cards,
                    content_rowid=rowid
                )
            """))
            conn.commit()
        logger.info("Database schema initialized")

    def card_count(self) -> int:
        """Get total number of cards in database"""
        if not self.__session:
            return 0

        try:
            count = self.__session.query(func.count(CardORM.id)).scalar()
            return count or 0
        except SQLAlchemyError:
            return 0

    def load_from_mtgjson(self, json_path: str, progress_callback=None):
        """
        Load cards from MTGJSON AllPrintings.json file

        Args:
            json_path: Path to AllPrintings.json
            progress_callback: Optional function to call with progress updates
        """
        if not self.__session:
            raise RuntimeError("Database not connected")

        logger.info(f"Loading cards from {json_path}...")

        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Extract the 'data' portion (MTGJSON v5 format has meta and data)
        if 'data' in json_data:
            data = json_data['data']
            logger.debug(f"MTGJSON version: {json_data.get('meta', {}).get('version', 'unknown')}")
        else:
            # Fallback for older format
            data = json_data

        total_cards = 0
        inserted_cards = 0

        # Process each set
        for set_code, set_data in data.items():
            cards = set_data.get('cards', [])
            total_cards += len(cards)

            for card in cards:
                try:
                    # Convert card data to ORM model
                    card_id = card.get('uuid', f"{set_code}_{card.get('name', 'unknown')}")

                    # Create ORM instance with JSON fields (SQLAlchemy handles serialization)
                    card_orm = CardORM(
                        id=card_id,
                        name=card.get('name'),
                        mana_cost=card.get('manaCost'),
                        cmc=card.get('manaValue', 0),
                        colors=card.get('colors', []),  # Direct list assignment
                        color_identity=card.get('colorIdentity', []),
                        type_line=card.get('type'),
                        types=card.get('types', []),
                        subtypes=card.get('subtypes', []),
                        oracle_text=card.get('text'),
                        power=card.get('power'),
                        toughness=card.get('toughness'),
                        loyalty=card.get('loyalty'),
                        set_code=set_code,
                        rarity=card.get('rarity'),
                        legalities=card.get('legalities', {}),
                        keywords=card.get('keywords', [])
                    )

                    # Merge (upsert) the card
                    self.__session.merge(card_orm)
                    inserted_cards += 1

                    # Commit in batches for better performance
                    if inserted_cards % 1000 == 0:
                        self.__session.commit()
                        if progress_callback:
                            progress_callback(inserted_cards, total_cards)

                except Exception as e:
                    logger.error(f"Error inserting card {card.get('name', 'unknown')}: {e}")
                    continue

        # Final commit
        self.__session.commit()

        # Rebuild FTS index
        logger.info("Rebuilding full-text search index...")
        with self.__engine.connect() as conn:
            conn.execute(text("INSERT INTO cards_fts(cards_fts) VALUES('rebuild')"))
            conn.commit()

        logger.info(f"Loaded {inserted_cards} cards from {len(data)} sets")
        return inserted_cards

    def get_card_by_name(self, name: str) -> Optional[MTGCard]:
        """
        Get a card by exact name (case-insensitive)

        Args:
            name: Card name to search for

        Returns:
            MTGCard object or None if not found
        """
        if not self.__session:
            return None

        try:
            # Case-insensitive search using func.lower()
            card_orm = self.__session.query(CardORM).filter(
                func.lower(CardORM.name) == func.lower(name)
            ).first()

            if card_orm:
                return orm_to_pydantic(card_orm)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching card: {e}")
            return None

    def _normalize_color(self, color: str) -> str:
        """
        Convert color names to single-letter codes

        Args:
            color: Color name or code (e.g., "Red", "red", "R")

        Returns:
            Single-letter color code (W, U, B, R, G, C)
        """
        color_map = {
            'white': 'W',
            'blue': 'U',
            'black': 'B',
            'red': 'R',
            'green': 'G',
            'colorless': 'C'
        }

        color_lower = color.lower().strip()

        if len(color) == 1:
            return color.upper()

        return color_map.get(color_lower, color.upper())

    def search_cards(
        self,
        query: Optional[str] = None,
        colors: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        cmc_min: Optional[float] = None,
        cmc_max: Optional[float] = None,
        rarity: Optional[str] = None,
        format_legality: Optional[Dict[str, str]] = None,
        strict_colors: bool = True,
        limit: int = 100
    ) -> List[MTGCard]:
        """
        Search for cards with various filters

        Args:
            query: Text to search in name/oracle text (uses FTS)
            colors: List of color codes or names
            types: List of types to filter by
            cmc_min: Minimum CMC
            cmc_max: Maximum CMC
            rarity: Card rarity
            format_legality: Format and status
            strict_colors: If True, only cards with EXACTLY these colors
            limit: Maximum results to return

        Returns:
            List of matching MTGCard objects
        """
        if not self.__session:
            return []

        try:
            # Start with base query
            if query:
                # Use FTS for text search (raw SQL required for FTS5)
                sql = text("""
                    SELECT cards.* FROM cards
                    JOIN cards_fts ON cards.rowid = cards_fts.rowid
                    WHERE cards_fts MATCH :query
                    LIMIT :limit
                """)
                result = self.__session.execute(sql, {"query": query, "limit": limit})
                # Get all rows and create ORM objects
                rows = result.fetchall()
                cards_orm = [CardORM(**dict(zip(result.keys(), row))) for row in rows]
            else:
                # Use SQLAlchemy ORM for filtering
                stmt = select(CardORM)

                # Add filters using SQLAlchemy expressions
                if colors:
                    colors = [self._normalize_color(c) for c in colors]

                    if strict_colors:
                        if len(colors) == 1:
                            # Mono-color: Match exactly this color OR colorless
                            color = colors[0]
                            stmt = stmt.where(
                                or_(
                                    CardORM.color_identity == json.dumps([color]),
                                    CardORM.color_identity == json.dumps([])
                                )
                            )
                        else:
                            # Multi-color: Exclude unwanted colors
                            all_colors = {'W', 'U', 'B', 'R', 'G'}
                            excluded_colors = all_colors - set(colors)

                            for excluded_color in excluded_colors:
                                # Use JSON contains check
                                stmt = stmt.where(
                                    ~func.json_extract(CardORM.color_identity, '$').contains(f'"{excluded_color}"')
                                )
                    else:
                        # Loose mode: Cards containing ANY of the specified colors
                        color_filters = []
                        for color in colors:
                            color_filters.append(
                                or_(
                                    func.json_extract(CardORM.colors, '$').contains(f'"{color}"'),
                                    func.json_extract(CardORM.color_identity, '$').contains(f'"{color}"')
                                )
                            )
                        if color_filters:
                            stmt = stmt.where(or_(*color_filters))

                if types:
                    for card_type in types:
                        stmt = stmt.where(
                            func.json_extract(CardORM.types, '$').contains(f'"{card_type}"')
                        )

                if cmc_min is not None:
                    stmt = stmt.where(CardORM.cmc >= cmc_min)

                if cmc_max is not None:
                    stmt = stmt.where(CardORM.cmc <= cmc_max)

                if rarity:
                    stmt = stmt.where(CardORM.rarity == rarity)

                if format_legality:
                    for format_name, status in format_legality.items():
                        status_capitalized = status.capitalize()
                        # Use JSON_EXTRACT for legalities
                        stmt = stmt.where(
                            func.json_extract(CardORM.legalities, f'$.{format_name.lower()}') == status_capitalized
                        )

                stmt = stmt.limit(limit)

                # Execute query
                result = self.__session.execute(stmt)
                cards_orm = result.scalars().all()

            # Convert ORM to Pydantic
            cards = orm_list_to_pydantic(cards_orm)
            logger.debug(f"Search returned {len(cards)} cards")
            return cards

        except SQLAlchemyError as e:
            logger.error(f"Error searching cards: {e}")
            return []

    def get_cards_by_format(self, format_name: str, status: str = "legal") -> List[MTGCard]:
        """
        Get all cards that have a specific legality status in a given format

        Args:
            format_name: The format to check
            status: The legality status to look for

        Returns:
            List of matching MTGCard objects
        """
        if not self.__session:
            return []

        try:
            stmt = select(CardORM).where(
                func.json_extract(CardORM.legalities, f'$.{format_name.lower()}') == status.capitalize()
            )

            result = self.__session.execute(stmt)
            cards_orm = result.scalars().all()

            return orm_list_to_pydantic(cards_orm)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching cards by format: {e}")
            return []

    def fuzzy_search(self, query: str, limit: int = 10) -> List[MTGCard]:
        """
        Fuzzy search for cards by name using LIKE

        Args:
            query: Search term
            limit: Maximum results

        Returns:
            List of matching MTGCard objects
        """
        if not self.__session:
            return []

        try:
            stmt = select(CardORM).where(
                CardORM.name.like(f"%{query}%")
            ).limit(limit)

            result = self.__session.execute(stmt)
            cards_orm = result.scalars().all()

            return orm_list_to_pydantic(cards_orm)
        except SQLAlchemyError as e:
            logger.error(f"Error in fuzzy search: {e}")
            return []
