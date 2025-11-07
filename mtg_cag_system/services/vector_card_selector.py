"""
Vector-enhanced card selector for synergy-based deck building.

This service combines:
1. Vector similarity search (find mechanically similar cards)
2. Archetype scoring (match user's deck strategy)
3. Synergy detection (cards that work well together)
"""

import logging
from typing import List, Dict, Optional, Tuple
from ..models.card import MTGCard
from .vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)


class VectorCardSelector:
    """
    Selects cards for deck building using vector similarity combined with archetype matching.

    Strategy:
    1. For each card in the current deck, find mechanically similar cards
    2. Score candidates based on:
       - Similarity to existing deck cards (synergy)
       - Archetype keyword matching (strategy adherence)
       - Avoid duplicates already in deck
    3. Rank and return best candidates
    """

    def __init__(self, vector_store: VectorStoreService):
        """
        Initialize selector with vector store.

        Args:
            vector_store: VectorStoreService instance with loaded embeddings
        """
        self.vector_store = vector_store
        self.logger = logger

    def select_synergistic_cards(
        self,
        current_deck: List[MTGCard],
        available_cards: List[MTGCard],
        archetype: str,
        archetype_keywords: List[str],
        needed: int,
        similarity_weight: float = 0.4,
        archetype_weight: float = 0.6,
    ) -> List[MTGCard]:
        """
        Select cards that synergize with the current deck while matching archetype.

        Args:
            current_deck: Cards already in the deck
            available_cards: Pool of candidates to choose from
            archetype: Deck archetype (e.g., 'aggro', 'control')
            archetype_keywords: Keywords for the archetype
            needed: Number of cards to select
            similarity_weight: Weight for synergy scoring (0-1)
            archetype_weight: Weight for archetype matching (0-1)

        Returns:
            List of best cards, sorted by combined score
        """
        if not current_deck or not available_cards:
            return []

        # Normalize weights
        total_weight = similarity_weight + archetype_weight
        similarity_weight = similarity_weight / total_weight
        archetype_weight = archetype_weight / total_weight

        # Get all synergy scores for available cards
        synergy_scores = self._compute_synergy_scores(current_deck, available_cards)

        # Score cards and combine with archetype matching
        scored_cards: List[Tuple[float, MTGCard]] = []

        for card in available_cards:
            # Synergy score (0-1 normalized)
            synergy_score = synergy_scores.get(card.id, 0.0)

            # Archetype score (0-1 normalized)
            archetype_score = self._score_archetype_match(card, archetype_keywords)

            # Combined score
            combined_score = (
                similarity_weight * synergy_score +
                archetype_weight * archetype_score
            )

            scored_cards.append((combined_score, card))

        # Sort by combined score (descending) and take top N
        scored_cards.sort(key=lambda x: x[0], reverse=True)
        selected = [card for score, card in scored_cards[:needed]]

        self.logger.debug(
            f"Selected {len(selected)} cards with synergy weights "
            f"(similarity={similarity_weight:.2f}, archetype={archetype_weight:.2f})"
        )

        return selected

    def _compute_synergy_scores(
        self,
        deck_cards: List[MTGCard],
        candidate_cards: List[MTGCard]
    ) -> Dict[str, float]:
        """
        Compute synergy score for each candidate based on similarity to deck cards.

        Strategy:
        - For each candidate, find similarity to each deck card
        - Average the similarities (represents how "in tune" it is with the deck)
        - Candidates similar to multiple deck cards score higher

        Args:
            deck_cards: Cards currently in deck
            candidate_cards: Candidate cards to evaluate

        Returns:
            Dict mapping card ID to synergy score (0-1)
        """
        synergy_scores: Dict[str, float] = {}

        if not deck_cards:
            return synergy_scores

        # Get unique names from deck for vector search
        # (avoid querying multiple printings of same card)
        deck_card_names = {card.name for card in deck_cards}

        # For each candidate, compute average similarity to deck cards
        for candidate in candidate_cards:
            if candidate.name in deck_card_names:
                # Already in deck, no synergy needed
                synergy_scores[candidate.id] = 0.0
                continue

            # Find how similar this candidate is to deck cards
            similarities = []
            for deck_card_name in deck_card_names:
                try:
                    # Query vector store for similarity
                    similar_cards = self.vector_store.find_similar_cards(
                        deck_card_name,
                        n_results=1  # Just need to check if candidate is in results
                    )

                    # Check if this candidate appears in the similar cards
                    for similar_card in similar_cards:
                        if similar_card['name'] == candidate.name:
                            # Distance to similarity score: distance ranges from 0 to 2
                            # Convert to similarity score 0-1
                            similarity = 1.0 - (similar_card['distance'] / 2.0)
                            similarities.append(max(0.0, similarity))
                            break
                except Exception as e:
                    self.logger.debug(f"Error computing similarity for {candidate.name}: {e}")
                    continue

            # Average similarity across all deck cards
            if similarities:
                synergy_scores[candidate.id] = sum(similarities) / len(similarities)
            else:
                synergy_scores[candidate.id] = 0.0

        return synergy_scores

    def _score_archetype_match(
        self,
        card: MTGCard,
        keywords: List[str]
    ) -> float:
        """
        Score how well a card matches the archetype keywords.

        Returns:
            Score from 0.0 to 1.0
        """
        if not keywords:
            return 0.5  # Neutral score if no keywords

        score = 0.0
        matches = 0

        # Check oracle text for keywords
        oracle_text = (card.oracle_text or "").lower()
        for keyword in keywords:
            if keyword.lower() in oracle_text:
                score += 1.0
                matches += 1

        # Check card keywords
        for card_keyword in card.keywords or []:
            for archetype_keyword in keywords:
                if archetype_keyword.lower() in card_keyword.lower():
                    score += 0.5
                    matches += 1

        # Normalize to 0-1 range
        # Maximum possible score: len(keywords) * 1.0 from oracle text
        max_score = len(keywords) * 1.0
        if max_score > 0:
            return min(1.0, score / max_score)
        else:
            return 0.5

    def find_missing_roles(
        self,
        current_deck: List[MTGCard],
        archetype: str,
        format_name: str = "standard"
    ) -> Dict[str, List[MTGCard]]:
        """
        Analyze the deck and find cards that could fill missing roles.

        Example: Aggro deck with only early creatures might need burn spells.

        Args:
            current_deck: Cards in the deck
            archetype: Deck archetype
            format_name: Format for filtering (e.g., 'standard')

        Returns:
            Dict mapping role (e.g., 'removal', 'card-draw') to suggested cards
        """
        roles = self._get_role_descriptions(archetype)
        missing_roles: Dict[str, List[MTGCard]] = {}

        for role_name, role_description in roles.items():
            # Find cards matching this role using concept search
            try:
                role_cards = self.vector_store.find_cards_by_concept(
                    role_description,
                    n_results=10,
                    filters={f'{format_name}_legal': True} if format_name else None
                )

                # Filter out cards already in deck
                deck_names = {card.name for card in current_deck}
                role_cards = [
                    card for card in role_cards
                    if card['name'] not in deck_names
                ]

                if role_cards:
                    missing_roles[role_name] = role_cards

            except Exception as e:
                self.logger.debug(f"Error finding {role_name} role: {e}")
                continue

        return missing_roles

    def _get_role_descriptions(self, archetype: str) -> Dict[str, str]:
        """Get natural language role descriptions for an archetype."""
        role_map = {
            'aggro': {
                'early-creatures': 'one mana creature, two mana creature, cheap creature',
                'burn': 'deal damage to opponent, lightning bolt, burn spell',
                'evasion': 'flying creature, unblockable creature, haste',
            },
            'control': {
                'removal': 'destroy target creature, kill creature, removal spell',
                'card-draw': 'draw cards, card advantage, dig deeper',
                'counterspell': 'counter spell, negate, cancel',
                'board-wipe': 'destroy all creatures, sweeper, board wipe',
            },
            'midrange': {
                'creatures': 'efficient creature, good value creature',
                'removal': 'destroy target creature, removal spell',
                'card-advantage': 'draw cards, card advantage, value',
            },
            'combo': {
                'tutors': 'search deck, find card, tutor',
                'synergy': 'goes infinite, combo pieces, synergistic',
                'protection': 'protect creature, counterspell, hexproof',
            },
            'tempo': {
                'creatures': 'evasive creature, creature with flash',
                'bounce': 'bounce spell, return creature, send back',
                'disruption': 'disrupt opponent, counter, tempo',
            },
            'ramp': {
                'mana': 'ramp spell, mana acceleration, land',
                'creatures': 'big creature, large creature, win condition',
                'fixing': 'mana fixing, color fixing, dual land',
            },
        }

        return role_map.get(archetype.lower(), {
            'creatures': 'creature',
            'removal': 'removal spell',
            'card-draw': 'draw cards',
        })
