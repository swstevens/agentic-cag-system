"""
Synergy Lookup Service

This service looks up synergistic cards based on complementary synergy patterns.
It matches cards with trigger patterns to cards with payoff patterns,
ignoring names and focusing purely on mechanical interactions.
"""

import logging
import time
from typing import Optional, List, Set
from ..models.responses import SynergyLookupResponse, SynergyResult
from .pattern_synergy_service import PatternSynergyService
from .card_lookup_service import CardLookupService

logger = logging.getLogger(__name__)


class SynergyLookupService:
    """
    Service for finding synergistic cards using pattern complementarity.

    Flow:
    1. Resolve card name to card object (via CardLookupService)
    2. Query pattern synergy service for complementary pattern matches
    3. Apply optional filters (format legality, archetype context)
    4. Return sorted results by synergy score
    """

    def __init__(
        self,
        pattern_synergy: PatternSynergyService,
        card_lookup: CardLookupService
    ):
        """
        Initialize synergy lookup service

        Args:
            pattern_synergy: PatternSynergyService for pattern-based matching
            card_lookup: CardLookupService for card resolution
        """
        self.pattern_synergy = pattern_synergy
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

            # Step 2: Build set of legal cards if format filter is specified
            legal_cards = None
            if format_filter:
                self._get_legal_cards_for_format(format_filter)
                # For now, format filtering returns None (not implemented)
                # This allows queries to work, we'll add format filtering later if needed

            # Step 3: Query pattern synergy service for synergistic cards
            synergy_results_raw = self.pattern_synergy.find_synergies(
                card_name=card_name,
                max_results=max_results * 2,  # Request 2x to account for filtering
                legal_cards=legal_cards
            )

            # Step 4: Convert to SynergyResult objects
            synergies = []
            for result in synergy_results_raw:
                # Skip very weak synergies
                if result["similarity_score"] < 0.5:
                    continue

                synergy = SynergyResult(
                    name=result["name"],
                    similarity_score=result["similarity_score"],
                    card_id=result.get("card_id", "")
                )
                synergies.append(synergy)

            # Step 5: Sort by synergy score (highest first)
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

    def _get_legal_cards_for_format(self, format_name: str) -> Optional[Set[str]]:
        """
        Build set of card names that are legal in a specific format

        Args:
            format_name: Format name (Standard, Modern, Commander, etc.)

        Returns:
            Set of legal card names, or None if format is unknown or no cards are legal
        """
        format_key_map = {
            "standard": "standard",
            "modern": "modern",
            "commander": "commander",
            "legacy": "legacy",
            "vintage": "vintage",
            "pioneer": "pioneer",
        }

        format_key = format_key_map.get(format_name.lower())
        if not format_key:
            logger.warning(f"Unknown format '{format_name}', skipping legality filter")
            return None

        # For now, return None to skip format filtering
        # The pattern service will return all results, and we filter afterwards if needed
        logger.info(f"Format filter '{format_key}' requested - returning all results (post-filter not yet implemented)")
        return None
