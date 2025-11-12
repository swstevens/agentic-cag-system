"""
Synergy Lookup Service

This service looks up synergistic cards for a given card using the vector store.
It leverages semantic similarity to find cards that work well together mechanically
and thematically.
"""

import logging
import time
from typing import Optional, List, Dict, Any
from ..models.card import MTGCard
from ..models.responses import SynergyLookupResponse, SynergyResult
from .vector_store_service import VectorStoreService
from .card_lookup_service import CardLookupService

logger = logging.getLogger(__name__)


class SynergyLookupService:
    """
    Service for finding synergistic cards using vector similarity.

    Flow:
    1. Resolve card name to card object (via CardLookupService)
    2. Query vector store for similar cards using VectorStoreService
    3. Apply optional filters (format legality, archetype context)
    4. Return sorted results by similarity score
    """

    def __init__(
        self,
        vector_store: VectorStoreService,
        card_lookup: CardLookupService
    ):
        """
        Initialize synergy lookup service

        Args:
            vector_store: VectorStoreService for similarity search
            card_lookup: CardLookupService for card resolution
        """
        self.vector_store = vector_store
        self.card_lookup = card_lookup

    async def lookup_synergies(
        self,
        card_name: str,
        max_results: int = 10,
        archetype: Optional[str] = None,
        format_filter: Optional[str] = None
    ) -> SynergyLookupResponse:
        """
        Look up synergistic cards for a given card

        Args:
            card_name: Name of the card to find synergies for
            max_results: Maximum number of results to return (1-100)
            archetype: Optional archetype for context (aggro, control, etc.)
            format_filter: Optional format to filter by legality

        Returns:
            SynergyLookupResponse with synergistic cards and metadata
        """
        start_time = time.time()

        try:
            # Step 1: Resolve card name to verify it exists
            source_card = self.card_lookup.get_card(card_name)
            if not source_card:
                logger.warning(f"Card '{card_name}' not found in database")
                return SynergyLookupResponse(
                    source_card=card_name,
                    synergies=[],
                    total_found=0,
                    execution_time=time.time() - start_time
                )

            # Step 2: Build optional filters for vector store query
            filters = None
            if format_filter:
                filters = self._build_format_filter(format_filter)

            # Step 3: Query vector store for similar cards
            similar_cards_raw = self.vector_store.find_similar_cards(
                card_name=card_name,
                n_results=max_results,
                filters=filters
            )

            # Step 4: Convert to SynergyResult objects and apply additional filtering
            synergies = []
            for card_data in similar_cards_raw:
                # Skip if similarity is too low (optional threshold)
                if card_data["distance"] > 0.5:  # ChromaDB returns distances (lower = more similar)
                    continue

                # Convert distance to similarity score (0.0-1.0, higher = more similar)
                similarity_score = 1.0 - min(card_data["distance"], 1.0)

                synergy = SynergyResult(
                    name=card_data["name"],
                    similarity_score=similarity_score,
                    card_id=card_data["id"]
                )
                synergies.append(synergy)

            # Step 5: Sort by similarity (highest first)
            synergies = sorted(synergies, key=lambda s: s.similarity_score, reverse=True)

            # Step 6: Apply max_results limit
            synergies = synergies[:max_results]

            logger.info(
                f"Found {len(synergies)} synergies for '{card_name}' "
                f"(archetype: {archetype}, format: {format_filter})"
            )

            return SynergyLookupResponse(
                source_card=card_name,
                synergies=synergies,
                total_found=len(synergies),
                execution_time=time.time() - start_time
            )

        except Exception as e:
            logger.error(f"Error looking up synergies for '{card_name}': {e}")
            return SynergyLookupResponse(
                source_card=card_name,
                synergies=[],
                total_found=0,
                execution_time=time.time() - start_time
            )

    def _build_format_filter(self, format_name: str) -> Dict[str, Any]:
        """
        Build ChromaDB filter for format legality

        Args:
            format_name: Format name (Standard, Modern, Commander, etc.)

        Returns:
            ChromaDB filter dictionary
        """
        format_filters = {
            "standard": {"standard_legal": True},
            "modern": {"modern_legal": True},
            "commander": {"commander_legal": True},
            "legacy": {"legacy_legal": True},
            "vintage": {"vintage_legal": True},
            "pioneer": {"pioneer_legal": True},
        }

        format_filter = format_filters.get(format_name.lower())
        if not format_filter:
            logger.warning(f"Unknown format '{format_name}', returning unfiltered results")
            return None

        return format_filter
