"""
Refactored Deck Builder Service (v2)

This version follows SOLID principles and depends on interfaces:
- ICardRepository for card data access
- IAnalyzer for deck quality analysis
- IValidator for deck legality validation

Changes from v1:
1. Depends on interfaces, not concrete implementations
2. Uses typed Pydantic models instead of Dict[str, Any]
3. Removes direct database access hacks
4. Cleaner separation of concerns
5. No more hidden dependencies
"""

from typing import List, Optional, Dict, Any
from ..interfaces.repository import ICardRepository, SearchCriteria
from ..interfaces.analyzer import IAnalyzer, AnalysisContext
from ..interfaces.validator import IValidator, ValidationRules
from ..models.card import MTGCard, CardColor
from ..models.deck_analysis import DeckAnalysisResult
from .vector_store_service import VectorStoreService
from .vector_card_selector import VectorCardSelector


class DeckBuilderServiceV2:
    """
    Refactored iterative deck building service.

    Dependencies are injected as interfaces, following Dependency Inversion Principle.
    """

    # Format-specific deck size requirements
    FORMAT_DECK_SIZES = {
        'Standard': 60,
        'Modern': 60,
        'Pioneer': 60,
        'Legacy': 60,
        'Vintage': 60,
        'Pauper': 60,
        'Commander': 100,
        'EDH': 100,
        'Brawl': 60,
        'Historic': 60,
        'Alchemy': 60,
        'Timeless': 60,
    }

    def __init__(
        self,
        repository: ICardRepository,
        analyzer: IAnalyzer,
        validator: Optional[IValidator] = None,
        max_iterations: int = 10,
        vector_store: Optional[VectorStoreService] = None
    ):
        """
        Initialize deck builder with interface dependencies.

        Args:
            repository: Card repository for data access (implements ICardRepository)
            analyzer: Deck analyzer for quality analysis (implements IAnalyzer)
            validator: Optional validator for legality checks (implements IValidator)
            max_iterations: Maximum build iterations
            vector_store: Optional VectorStoreService for synergy-based card selection
        """
        self.repository = repository
        self.analyzer = analyzer
        self.validator = validator
        self.max_iterations = max_iterations

        # Vector search for synergy detection
        self.vector_store = vector_store
        self.vector_selector = VectorCardSelector(vector_store) if vector_store else None

        # Deck state
        self._deck: List[MTGCard] = []
        self._candidates: List[MTGCard] = []

    async def build_deck(
        self,
        colors: List[str],
        archetype: str,
        deck_format: str = "Standard"
    ) -> Dict[str, Any]:
        """
        Build a complete, legal deck iteratively.

        Args:
            colors: Deck colors (e.g., ["Red", "Blue"])
            archetype: Deck archetype (e.g., "aggro", "control")
            deck_format: Format (e.g., "Standard", "Modern")

        Returns:
            Dict with 'deck', 'analysis', 'iterations', and 'is_valid'
        """
        target_size = self.FORMAT_DECK_SIZES.get(deck_format, 60)
        print(f"Building {archetype} deck in {deck_format} ({target_size} cards)")

        # Reset state
        self._deck = []
        self._candidates = []

        # Convert color strings to CardColor enums
        color_enums = [self._parse_color(c) for c in colors if c]

        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'=' * 80}")
            print(f"ITERATION {iteration}")
            print(f"{'=' * 80}")

            current_size = len(self._deck)
            print(f"Current deck size: {current_size}/{target_size}")

            # Check if deck is complete
            if current_size == target_size:
                print("\n✅ DECK COMPLETE!")
                break

            # Fetch cards based on requirements
            cards_needed = target_size - current_size
            print(f"Cards needed: {cards_needed}")

            # Search for cards matching archetype
            new_cards = await self._fetch_cards(
                colors=color_enums,
                archetype=archetype,
                format=deck_format,
                limit=cards_needed * 2  # Fetch more than needed for selection
            )

            # Score and select best cards
            selected_cards = self._select_best_cards(
                cards=new_cards,
                archetype=archetype,
                needed=cards_needed
            )

            # Add to deck
            self._deck.extend(selected_cards)
            print(f"Added {len(selected_cards)} cards")

            if iteration >= self.max_iterations:
                print(f"\n⚠️  Reached maximum iterations ({self.max_iterations})")
                break

        # Analyze final deck (if analyzer is available)
        analysis_result = None
        if self.analyzer:
            print(f"\n{'=' * 80}")
            print("ANALYZING DECK QUALITY")
            print(f"{'=' * 80}")

            analysis_context = AnalysisContext(
                archetype=archetype,
                format=deck_format,
                target_deck_size=target_size
            )

            analysis_result = await self.analyzer.analyze(self._deck, analysis_context)
        else:
            print(f"\n{'=' * 80}")
            print("DECK BUILD COMPLETE (Analysis skipped - analyzer not available)")
            print(f"{'=' * 80}")

        # Return results
        return {
            'deck': self._deck,
            'analysis': analysis_result,
            'is_valid': len(self._deck) == target_size,
            'deck_size': len(self._deck),
            'target_size': target_size,
        }

    async def _fetch_cards(
        self,
        colors: List[CardColor],
        archetype: str,
        format: str,
        limit: int
    ) -> List[MTGCard]:
        """
        Fetch cards matching requirements from repository.

        Args:
            colors: List of CardColor enums
            archetype: Deck archetype
            format: Format for legality
            limit: Maximum cards to fetch

        Returns:
            List of MTGCard objects
        """
        criteria = SearchCriteria(
            colors=colors if colors else None,
            format=format,
            limit=limit
        )

        cards = self.repository.search(criteria)
        print(f"Found {len(cards)} matching cards")
        return cards

    def _select_best_cards(
        self,
        cards: List[MTGCard],
        archetype: str,
        needed: int
    ) -> List[MTGCard]:
        """
        Score and select best cards for archetype.

        Optionally uses vector search for synergy-based selection if vector_store is available.

        Args:
            cards: Available cards
            archetype: Deck archetype
            needed: Number of cards to select

        Returns:
            Best cards for the archetype
        """
        # Get archetype keywords
        archetype_keywords = self._get_archetype_keywords(archetype)

        # If we have vector store and deck cards, use synergy-based selection
        if self.vector_selector and len(self._deck) > 0:
            try:
                selected = self.vector_selector.select_synergistic_cards(
                    current_deck=self._deck,
                    available_cards=cards,
                    archetype=archetype,
                    archetype_keywords=archetype_keywords,
                    needed=needed,
                    similarity_weight=0.4,  # Weight synergy
                    archetype_weight=0.6,   # Weight archetype adherence
                )
                print(f"Using vector-enhanced selection: {len(selected)} cards selected by synergy")
                return selected
            except Exception as e:
                print(f"⚠️  Vector selection failed: {e}, falling back to keyword scoring")
                # Fall back to traditional scoring if vector search fails

        # Traditional scoring based on archetype keywords
        scored_cards = []
        for card in cards:
            score = self._score_card(card, archetype_keywords)
            scored_cards.append((score, card))

        # Sort by score descending
        scored_cards.sort(key=lambda x: x[0], reverse=True)

        # Take top N cards
        selected = [card for score, card in scored_cards[:needed]]
        return selected

    def _score_card(self, card: MTGCard, keywords: List[str]) -> float:
        """
        Score card based on how well it matches archetype keywords.

        Args:
            card: Card to score
            keywords: Archetype keywords to match

        Returns:
            Score (higher is better)
        """
        score = 0.0

        # Check oracle text for keywords
        oracle_text = (card.oracle_text or "").lower()
        for keyword in keywords:
            if keyword.lower() in oracle_text:
                score += 10.0

        # Check card keywords
        for card_keyword in card.keywords:
            if any(kw.lower() in card_keyword.lower() for kw in keywords):
                score += 5.0

        # Bonus for good CMC ranges by archetype
        # (This is simplified; real logic would be more sophisticated)
        score += 1.0  # Base score

        return score

    def _get_archetype_keywords(self, archetype: str) -> List[str]:
        """Get relevant keywords for an archetype."""
        keywords_map = {
            'aggro': ['haste', 'attack', 'damage', 'burn', 'fast', 'aggressive'],
            'control': ['counter', 'draw', 'removal', 'destroy', 'exile', 'board wipe'],
            'midrange': ['value', 'card advantage', 'removal', 'creature'],
            'combo': ['tutor', 'search', 'combo', 'infinite', 'win the game'],
            'tempo': ['bounce', 'counter', 'flash', 'instant', 'disrupt'],
            'ramp': ['mana', 'land', 'ramp', 'acceleration', 'big creatures'],
        }
        return keywords_map.get(archetype.lower(), [])

    def _parse_color(self, color: str) -> CardColor:
        """Parse color string to CardColor enum."""
        color_map = {
            'white': CardColor.WHITE,
            'blue': CardColor.BLUE,
            'black': CardColor.BLACK,
            'red': CardColor.RED,
            'green': CardColor.GREEN,
            'colorless': CardColor.COLORLESS,
            'w': CardColor.WHITE,
            'u': CardColor.BLUE,
            'b': CardColor.BLACK,
            'r': CardColor.RED,
            'g': CardColor.GREEN,
            'c': CardColor.COLORLESS,
        }
        return color_map.get(color.lower(), CardColor.COLORLESS)

    def get_deck(self) -> List[MTGCard]:
        """Get current deck (for external access)."""
        return self._deck.copy()

    def get_deck_size(self) -> int:
        """Get current deck size."""
        return len(self._deck)
