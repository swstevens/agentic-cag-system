"""
Vector Store Service for MTG Card Similarity Search

This service uses ChromaDB to store and query card embeddings.
Embeddings are computed once and persisted to disk for reuse.

Synergy Mode:
This service can be configured to use synergy-focused embeddings that capture
mechanical interactions between cards rather than just mechanical similarity.
This requires synergy patterns to be pre-extracted via scripts/extract_synergy_patterns.py
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from ..models.card import MTGCard
from .database_service import DatabaseService

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Manages vector embeddings for MTG cards using ChromaDB.

    Features:
    - One-time embedding generation from database
    - Persistent storage (embeddings saved to disk)
    - Fast similarity search
    - Metadata filtering (colors, types, formats)
    """

    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "mtg_cards",
        embedding_model: str = "all-MiniLM-L6-v2",
        synergy_patterns_path: Optional[str] = "./data/synergy_patterns.json"
    ):
        """
        Initialize vector store service

        Args:
            persist_directory: Directory to persist embeddings
            collection_name: Name of the ChromaDB collection
            embedding_model: Sentence transformer model name
            synergy_patterns_path: Path to synergy patterns JSON file (optional)
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.synergy_patterns = {}

        # Load synergy patterns if available
        if synergy_patterns_path:
            synergy_path = Path(synergy_patterns_path)
            if synergy_path.exists():
                try:
                    with open(synergy_path, 'r') as f:
                        self.synergy_patterns = json.load(f)
                    logger.info(f"Loaded synergy patterns for {len(self.synergy_patterns)} cards")
                except Exception as e:
                    logger.warning(f"Could not load synergy patterns: {e}")
            else:
                logger.debug(f"Synergy patterns file not found at {synergy_patterns_path}")

        # Create persist directory if it doesn't exist
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))

        # Use sentence transformers for embeddings
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "MTG card embeddings for similarity search"}
        )

        logger.info(f"Vector store initialized at {self.persist_directory}")
        logger.info(f"Collection '{collection_name}' has {self.collection.count()} embeddings")

    def is_initialized(self) -> bool:
        """Check if embeddings have been generated"""
        return self.collection.count() > 0

    def _create_card_text(self, card: MTGCard) -> str:
        """
        Create searchable text representation of a card

        Combines multiple card attributes to create a rich text representation
        that captures mechanics, types, effects, and synergy signals.

        Args:
            card: MTGCard to convert to text

        Returns:
            Text representation for embedding
        """
        parts = []

        # Card name
        parts.append(f"Name: {card.name}")

        # Type line
        if card.type_line:
            parts.append(f"Type: {card.type_line}")

        # Mana cost and CMC
        if card.mana_cost:
            parts.append(f"Cost: {card.mana_cost}")

        # Colors
        if card.colors:
            parts.append(f"Colors: {', '.join(card.colors)}")

        # Keywords (important for mechanics)
        if card.keywords:
            parts.append(f"Keywords: {', '.join(card.keywords)}")

        # Oracle text (most important for similarity)
        if card.oracle_text:
            parts.append(f"Text: {card.oracle_text}")

        # Power/Toughness for creatures
        if card.power and card.toughness:
            parts.append(f"Stats: {card.power}/{card.toughness}")

        # Subtypes (for tribal synergies)
        if card.subtypes:
            parts.append(f"Subtypes: {', '.join(card.subtypes)}")

        # Synergy signals (if available)
        if card.name in self.synergy_patterns:
            synergy_data = self.synergy_patterns[card.name]
            synergy_text = synergy_data.get("synergy_text", "")
            if synergy_text:
                parts.append(f"Synergy: {synergy_text}")

        return " | ".join(parts)

    def _create_metadata(self, card: MTGCard) -> Dict[str, Any]:
        """
        Create metadata for filtering

        Args:
            card: MTGCard to extract metadata from

        Returns:
            Metadata dictionary for ChromaDB
        """
        return {
            "name": card.name,
            "cmc": card.cmc,
            "colors": ",".join(card.colors) if card.colors else "",
            "color_identity": ",".join(card.color_identity) if card.color_identity else "",
            "types": ",".join(card.types) if card.types else "",
            "subtypes": ",".join(card.subtypes) if card.subtypes else "",
            "rarity": card.rarity,
            "set_code": card.set_code,
            # Store legalities as separate fields for filtering
            "standard_legal": card.legalities.get("standard", "").lower() == "legal",
            "modern_legal": card.legalities.get("modern", "").lower() == "legal",
            "commander_legal": card.legalities.get("commander", "").lower() == "legal",
        }

    def build_embeddings(
        self,
        database_service: DatabaseService,
        batch_size: int = 1000,
        progress_callback: Optional[callable] = None,
        force_rebuild: bool = False
    ):
        """
        Build embeddings for all cards in the database (ONE-TIME OPERATION)

        This should only be run once when the vector store is empty.
        Embeddings are persisted to disk and reused on subsequent runs.

        Args:
            database_service: Database service to fetch cards from
            batch_size: Number of cards to process at once
            progress_callback: Optional callback(current, total) for progress
            force_rebuild: Force rebuild even if embeddings exist (useful when synergy patterns change)
        """
        if self.is_initialized() and not force_rebuild:
            logger.warning("Embeddings already exist. Skipping build. Use force_rebuild=True to override.")
            return

        if force_rebuild and self.is_initialized():
            logger.info("Force rebuild requested. Clearing existing embeddings...")
            try:
                # Delete and recreate collection
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": "MTG card embeddings for synergy search"}
                )
                logger.info("Existing embeddings cleared.")
            except Exception as e:
                logger.warning(f"Could not clear embeddings: {e}")

        logger.info("Building embeddings for all cards (this may take a while)...")
        if self.synergy_patterns:
            logger.info(f"Using synergy patterns from {len(self.synergy_patterns)} cards")

        # Get total count
        total_cards = database_service.card_count()
        logger.info(f"Found {total_cards} cards to process")

        # Process in batches
        processed = 0
        offset = 0

        while offset < total_cards:
            # Fetch batch of cards with proper offset
            cards = database_service.search_cards(
                query=None,
                limit=batch_size,
                offset=offset
            )

            if not cards:
                break

            # Prepare data for ChromaDB
            ids = [card.id for card in cards]
            documents = [self._create_card_text(card) for card in cards]
            metadatas = [self._create_metadata(card) for card in cards]

            # Add to collection (embeddings computed automatically)
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            processed += len(cards)
            offset += batch_size

            logger.info(f"Processed {processed}/{total_cards} cards")

            if progress_callback:
                progress_callback(processed, total_cards)

        logger.info(f"✅ Embeddings built for {processed} cards and persisted to disk")
        if self.synergy_patterns:
            logger.info(f"✅ Synergy patterns integrated for enhanced similarity search")

    def find_similar_cards(
        self,
        card_name: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find cards similar to a given card

        Args:
            card_name: Name of the card to find similar cards for
            n_results: Number of similar cards to return
            filters: Optional metadata filters (e.g., {"standard_legal": True})

        Returns:
            List of similar cards with similarity scores
        """
        # Query by card name to get its embedding
        results = self.collection.query(
            query_texts=[f"Name: {card_name}"],
            n_results=n_results + 1,  # +1 to exclude the query card itself
            where=filters
        )

        if not results["ids"] or not results["ids"][0]:
            logger.warning(f"No results found for card: {card_name}")
            return []

        # Format results
        similar_cards = []
        for i, card_id in enumerate(results["ids"][0]):
            # Skip the query card itself
            if results["metadatas"][0][i]["name"].lower() == card_name.lower():
                continue

            similar_cards.append({
                "id": card_id,
                "name": results["metadatas"][0][i]["name"],
                "distance": results["distances"][0][i],
                "metadata": results["metadatas"][0][i]
            })

        return similar_cards[:n_results]

    def find_cards_by_concept(
        self,
        concept: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find cards matching a concept or strategy

        Examples:
        - "cards that create tokens"
        - "removal spells"
        - "mana ramp"
        - "card draw"

        Args:
            concept: Natural language concept description
            n_results: Number of cards to return
            filters: Optional metadata filters

        Returns:
            List of matching cards with similarity scores
        """
        results = self.collection.query(
            query_texts=[concept],
            n_results=n_results,
            where=filters
        )

        if not results["ids"] or not results["ids"][0]:
            logger.warning(f"No results found for concept: {concept}")
            return []

        # Format results
        cards = []
        for i, card_id in enumerate(results["ids"][0]):
            cards.append({
                "id": card_id,
                "name": results["metadatas"][0][i]["name"],
                "distance": results["distances"][0][i],
                "metadata": results["metadatas"][0][i]
            })

        return cards

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            "total_embeddings": self.collection.count(),
            "persist_directory": str(self.persist_directory),
            "collection_name": self.collection_name,
            "is_initialized": self.is_initialized()
        }
