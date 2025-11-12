"""
Pattern-Based Synergy Service

This service finds synergies by matching complementary synergy patterns.
It completely ignores card names and focuses purely on mechanical interactions.

Examples of synergistic pairs:
- "gains_life" (trigger) + "life_gain_payoff" (payoff) = synergy
- "etb_trigger" (trigger) + "etb_payoff" (payoff) = synergy
- "creature_dies" (trigger) + "death_payoff" (payoff) = synergy
"""

import json
import logging
import time
from typing import Optional, List, Dict, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class PatternSynergyService:
    """
    Service for finding synergistic cards based on complementary patterns.

    Instead of semantic similarity, this matches cards that have complementary
    mechanical patterns (e.g., trigger + payoff).
    """

    # Define pattern complementarity - which patterns synergize with which
    PATTERN_COMPLEMENTS = {
        # Life gain synergies
        "gains_life": ["life_gain_payoff"],
        "life_gain_payoff": ["gains_life"],

        # ETB synergies
        "etb_trigger": ["etb_payoff"],
        "etb_payoff": ["etb_trigger"],

        # Death trigger synergies
        "creature_dies": ["death_payoff"],
        "death_payoff": ["creature_dies"],

        # Sacrifice synergies
        "sacrifice_outlet": ["sacrifice_payoff"],
        "sacrifice_payoff": ["sacrifice_outlet"],

        # Discard synergies
        "discard_trigger": ["discard_payoff"],
        "discard_payoff": ["discard_trigger"],

        # Spell cast synergies
        "spell_cast": ["storm_combo"],
        "storm_combo": ["spell_cast"],

        # Token synergies
        "token_creation": ["token_payoff"],
        "token_payoff": ["token_creation"],

        # Card draw synergies
        "card_draw": ["draw_payoff"],
        "draw_payoff": ["card_draw"],

        # Mana synergies
        "mana_ramp": ["mana_sink"],
        "mana_sink": ["mana_ramp"],

        # Color/type synergies
        "color_matters": ["color_matters", "lord_effects"],
        "lord_effects": ["color_matters"],

        # Recursion and graveyard
        "recursion": ["creature_dies", "death_payoff"],
        "creature_dies": ["recursion"],
        "death_payoff": ["recursion"],

        # Flicker synergies
        "flicker": ["etb_trigger", "etb_payoff"],
        "etb_trigger": ["flicker"],
        "etb_payoff": ["flicker"],

        # Card advantage
        "card_advantage": ["card_draw", "draw_payoff"],
    }

    # Score multipliers for different types of synergies
    SYNERGY_SCORES = {
        # Direct trigger-payoff pairs (highest priority)
        ("gains_life", "life_gain_payoff"): 1.0,
        ("life_gain_payoff", "gains_life"): 1.0,
        ("etb_trigger", "etb_payoff"): 0.95,
        ("etb_payoff", "etb_trigger"): 0.95,
        ("creature_dies", "death_payoff"): 0.95,
        ("death_payoff", "creature_dies"): 0.95,
        ("sacrifice_outlet", "sacrifice_payoff"): 0.95,
        ("sacrifice_payoff", "sacrifice_outlet"): 0.95,
        ("discard_trigger", "discard_payoff"): 0.90,
        ("discard_payoff", "discard_trigger"): 0.90,
        ("spell_cast", "storm_combo"): 0.90,
        ("storm_combo", "spell_cast"): 0.90,
        ("token_creation", "token_payoff"): 0.90,
        ("token_payoff", "token_creation"): 0.90,
        ("card_draw", "draw_payoff"): 0.85,
        ("draw_payoff", "card_draw"): 0.85,

        # Secondary synergies (lower priority but still good)
        ("flicker", "etb_trigger"): 0.85,
        ("flicker", "etb_payoff"): 0.80,
        ("recursion", "creature_dies"): 0.75,
        ("recursion", "death_payoff"): 0.75,
    }

    def __init__(self, synergy_patterns_path: str = "./data/synergy_patterns.json"):
        """
        Initialize pattern synergy service

        Args:
            synergy_patterns_path: Path to synergy patterns JSON file
        """
        self.synergy_patterns = {}
        self.card_patterns_map = {}  # card_id -> set of patterns
        self.pattern_cards_map = {}  # pattern -> set of card_ids

        self._load_patterns(synergy_patterns_path)

    def _load_patterns(self, synergy_patterns_path: str):
        """Load synergy patterns from file"""
        patterns_path = Path(synergy_patterns_path)
        if not patterns_path.exists():
            logger.warning(f"Synergy patterns file not found at {synergy_patterns_path}")
            return

        try:
            with open(patterns_path, 'r') as f:
                self.synergy_patterns = json.load(f)

            # Build reverse lookup maps
            for card_name, data in self.synergy_patterns.items():
                patterns = set(data.get("patterns", []))
                self.card_patterns_map[card_name] = patterns

                for pattern in patterns:
                    if pattern not in self.pattern_cards_map:
                        self.pattern_cards_map[pattern] = set()
                    self.pattern_cards_map[pattern].add(card_name)

            logger.info(f"Loaded synergy patterns for {len(self.synergy_patterns)} cards")
            logger.info(f"Pattern distribution: {len(self.pattern_cards_map)} unique patterns")
        except Exception as e:
            logger.error(f"Failed to load synergy patterns: {e}")

    def find_synergies(
        self,
        card_name: str,
        max_results: int = 10,
        legal_cards: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find synergistic cards based on pattern complementarity.

        Args:
            card_name: Name of the card to find synergies for
            max_results: Maximum number of results to return
            legal_cards: Optional set of card names that are legal in a format

        Returns:
            List of (card_name, synergy_score) tuples sorted by score
        """
        start_time = time.time()

        # Get patterns for the source card
        source_patterns = self.card_patterns_map.get(card_name, set())
        if not source_patterns:
            logger.warning(f"Card '{card_name}' has no synergy patterns")
            return []

        # Find complementary cards
        synergy_scores = {}

        for source_pattern in source_patterns:
            # Get cards that match complementary patterns
            for complement_pattern in self.PATTERN_COMPLEMENTS.get(source_pattern, []):
                if complement_pattern not in self.pattern_cards_map:
                    continue

                for candidate_card in self.pattern_cards_map[complement_pattern]:
                    # Skip the source card itself
                    if candidate_card == card_name:
                        continue

                    # Skip if not legal (if filter provided)
                    if legal_cards is not None and candidate_card not in legal_cards:
                        continue

                    # Calculate synergy score
                    candidate_patterns = self.card_patterns_map[candidate_card]
                    score = self._calculate_synergy_score(source_patterns, candidate_patterns)

                    # Keep the highest score for this candidate
                    if candidate_card not in synergy_scores or score > synergy_scores[candidate_card]:
                        synergy_scores[candidate_card] = score

        # Sort by score and limit results
        sorted_synergies = sorted(
            [(card, score) for card, score in synergy_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:max_results]

        # Format results
        results = [
            {
                "name": card,
                "similarity_score": score,
                "card_id": f"pattern-{i}"  # Placeholder ID
            }
            for i, (card, score) in enumerate(sorted_synergies)
        ]

        execution_time = time.time() - start_time
        logger.info(
            f"Found {len(results)} synergies for '{card_name}' "
            f"(time: {execution_time:.3f}s)"
        )

        return results

    def _calculate_synergy_score(self, source_patterns: Set[str], candidate_patterns: Set[str]) -> float:
        """
        Calculate synergy score between two sets of patterns.

        Prioritizes direct trigger-payoff pairs over general overlap.

        Args:
            source_patterns: Set of patterns for source card
            candidate_patterns: Set of patterns for candidate card

        Returns:
            Synergy score (0.0-1.0)
        """
        max_score = 0.0

        # Check for direct complementary pairs (highest priority)
        for source_p in source_patterns:
            for candidate_p in candidate_patterns:
                pair_score = self.SYNERGY_SCORES.get((source_p, candidate_p), 0.0)
                if pair_score > max_score:
                    max_score = pair_score

        # If no direct pairs found, check for indirect complementarity
        if max_score == 0.0:
            for source_p in source_patterns:
                complements = self.PATTERN_COMPLEMENTS.get(source_p, [])
                for complement in complements:
                    if complement in candidate_patterns:
                        # Found a complementary pattern
                        max_score = 0.5  # Lower score for indirect matches
                        break

        return max_score

    def get_pattern_info(self, card_name: str) -> Dict[str, Any]:
        """Get pattern information for a card"""
        if card_name not in self.synergy_patterns:
            return {"found": False}

        data = self.synergy_patterns[card_name]
        return {
            "found": True,
            "card_name": card_name,
            "patterns": data.get("patterns", []),
            "synergy_text": data.get("synergy_text", ""),
            "pattern_count": data.get("pattern_count", 0)
        }
