"""
Deck Repository for V3 architecture.

Provides high-level interface for deck persistence with CRUD operations.
"""

import json
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from .database_service import DatabaseService
from ..models.deck import Deck


class DeckRepository:
    """
    Repository for deck persistence.

    Provides CRUD operations for saving, loading, updating, and deleting decks.
    """

    def __init__(self, database_service: DatabaseService):
        """
        Initialize deck repository.

        Args:
            database_service: Database service instance
        """
        self.db = database_service

    def save_deck(
        self,
        deck: Deck,
        name: str,
        description: Optional[str] = None,
        quality_score: Optional[float] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Save a new deck to the database.

        Args:
            deck: Deck object to save
            name: Human-readable name for the deck
            description: Optional description
            quality_score: Optional quality score from verification
            user_id: Optional user ID for multi-user support

        Returns:
            Deck ID (UUID)
        """
        deck_id = str(uuid.uuid4())

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Serialize deck to JSON
            deck_data = json.dumps(deck.model_dump())
            colors_json = json.dumps(deck.colors)

            cursor.execute("""
                INSERT INTO decks (
                    id, name, description, format, archetype, colors,
                    deck_data, quality_score, total_cards, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deck_id,
                name,
                description,
                deck.format,
                deck.archetype,
                colors_json,
                deck_data,
                quality_score,
                deck.total_cards,
                user_id
            ))

        return deck_id

    def get_deck_by_id(self, deck_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a deck by ID.

        Args:
            deck_id: Deck UUID

        Returns:
            Dictionary with deck data and metadata, or None if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM decks WHERE id = ?
            """, (deck_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def list_decks(
        self,
        format_filter: Optional[str] = None,
        archetype_filter: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List decks with optional filters.

        Args:
            format_filter: Filter by format (e.g., "Standard", "Commander")
            archetype_filter: Filter by archetype (e.g., "Aggro", "Control")
            user_id: Filter by user ID
            limit: Maximum results to return
            offset: Number of results to skip (for pagination)

        Returns:
            List of deck dictionaries with metadata
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM decks WHERE 1=1"
            params = []

            if format_filter and format_filter != "All Formats":
                query += " AND LOWER(format) = LOWER(?)"
                params.append(format_filter)

            if archetype_filter and archetype_filter != "All Archetypes":
                query += " AND LOWER(archetype) = LOWER(?)"
                params.append(archetype_filter)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            # Order by most recently created
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.append(limit)
            params.append(offset)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_dict(row) for row in rows]

    def update_deck(
        self,
        deck_id: str,
        deck: Deck,
        name: Optional[str] = None,
        description: Optional[str] = None,
        quality_score: Optional[float] = None
    ) -> bool:
        """
        Update an existing deck.

        Args:
            deck_id: Deck UUID
            deck: Updated deck object
            name: Optional new name
            description: Optional new description
            quality_score: Optional new quality score

        Returns:
            True if updated, False if deck not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Build update query dynamically based on what's provided
            update_fields = []
            params = []

            # Deck data always updated
            deck_data = json.dumps(deck.model_dump())
            colors_json = json.dumps(deck.colors)

            update_fields.extend([
                "deck_data = ?",
                "format = ?",
                "archetype = ?",
                "colors = ?",
                "total_cards = ?",
                "updated_at = CURRENT_TIMESTAMP"
            ])
            params.extend([
                deck_data,
                deck.format,
                deck.archetype,
                colors_json,
                deck.total_cards
            ])

            if name is not None:
                update_fields.append("name = ?")
                params.append(name)

            if description is not None:
                update_fields.append("description = ?")
                params.append(description)

            if quality_score is not None:
                update_fields.append("quality_score = ?")
                params.append(quality_score)

            params.append(deck_id)

            query = f"""
                UPDATE decks
                SET {', '.join(update_fields)}
                WHERE id = ?
            """

            cursor.execute(query, params)

            return cursor.rowcount > 0

    def delete_deck(self, deck_id: str) -> bool:
        """
        Delete a deck by ID.

        Args:
            deck_id: Deck UUID

        Returns:
            True if deleted, False if deck not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
            return cursor.rowcount > 0

    def get_deck_count(
        self,
        format_filter: Optional[str] = None,
        archetype_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> int:
        """
        Get count of decks matching filters.

        Args:
            format_filter: Filter by format
            archetype_filter: Filter by archetype
            user_id: Filter by user ID

        Returns:
            Count of matching decks
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT COUNT(*) FROM decks WHERE 1=1"
            params = []

            if format_filter:
                query += " AND LOWER(format) = LOWER(?)"
                params.append(format_filter)

            if archetype_filter:
                query += " AND LOWER(archetype) = LOWER(?)"
                params.append(archetype_filter)

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """
        Convert database row to dictionary with JSON parsing.

        Args:
            row: SQLite row object

        Returns:
            Dictionary with parsed fields
        """
        data = dict(row)

        # Parse JSON fields
        if data.get('deck_data'):
            try:
                data['deck'] = json.loads(data['deck_data'])
            except json.JSONDecodeError:
                data['deck'] = None

        if data.get('colors'):
            try:
                data['colors'] = json.loads(data['colors'])
            except json.JSONDecodeError:
                data['colors'] = []

        return data
