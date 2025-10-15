"""
Iterative Deck Builder Service

This service coordinates agents to build a complete, legal deck through iteration:
1. Fetch initial cards based on requirements
2. Validate deck
3. If invalid, identify issues and fetch more/different cards
4. Repeat until deck is legal and complete
"""

from typing import List, Dict, Any, Optional
from ..utils.deck_parser import DeckParser
from ..models.card import MTGCard
from ..agents.knowledge_fetch_agent import KnowledgeFetchAgent
from ..agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from .card_lookup_service import CardLookupService


class DeckBuilderService:
    """
    Iterative deck building service that produces complete, legal decks
    """

    def __init__(
        self,
        knowledge_agent: KnowledgeFetchAgent,
        symbolic_agent: SymbolicReasoningAgent,
        card_lookup: CardLookupService,
        max_iterations: int = 10
    ):
        """
        Initialize deck builder

        Args:
            knowledge_agent: Agent for fetching cards
            symbolic_agent: Agent for validation
            card_lookup: Direct card lookup service
            max_iterations: Maximum iteration attempts
        """
        self.knowledge_agent = knowledge_agent
        self.symbolic_agent = symbolic_agent
        self.card_lookup = card_lookup
        self.max_iterations = max_iterations

    async def build_deck(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a complete, legal deck through iteration

        Args:
            requirements: Deck requirements (colors, format, archetype, etc.)

        Returns:
            Dictionary with final deck and build history
        """
        print("\n" + "=" * 80)
        print("ITERATIVE DECK BUILDING")
        print("=" * 80)
        print(f"Requirements: {requirements}")
        print()

        # Extract requirements
        colors = requirements.get('colors', ['R'])
        deck_format = requirements.get('format', 'Standard')
        archetype = requirements.get('archetype', 'aggro')
        target_size = requirements.get('deck_size', 60)

        # Initialize deck
        deck = []
        card_names_tried = set()
        iterations = []

        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'=' * 80}")
            print(f"ITERATION {iteration}")
            print(f"{'=' * 80}")

            # Step 1: Assess current deck state
            current_size = len(deck)
            print(f"Current deck size: {current_size}/{target_size}")

            if current_size > 0:
                # Validate current deck
                validation = await self._validate_deck(deck, deck_format)
                print(f"Validation: {validation}")

                # Check if deck is complete and legal
                if validation['valid'] and current_size >= target_size:
                    print(f"\n✅ DECK COMPLETE AND LEGAL!")
                    break

                # Remove illegal cards
                if not validation['validations'].get('format_legal', True):
                    print("\n⚠️  Removing illegal cards...")
                    deck = self._remove_illegal_cards(deck, deck_format, validation)
                    print(f"   Deck size after removal: {len(deck)}")

            # Step 2: Determine what cards are needed
            cards_needed = target_size - len(deck)
            print(f"\nCards needed: {cards_needed}")

            if cards_needed <= 0:
                continue

            # Step 3: Fetch new cards based on requirements
            new_cards = await self._fetch_cards_for_requirements(
                colors=colors,
                archetype=archetype,
                deck_format=deck_format,
                cards_needed=cards_needed,
                already_tried=card_names_tried
            )

            # Step 4: Add cards to deck (respecting 4-copy limit)
            added_count = self._add_cards_to_deck(deck, new_cards, cards_needed)
            print(f"Added {added_count} cards to deck")

            # Track iteration
            iterations.append({
                'iteration': iteration,
                'deck_size': len(deck),
                'cards_added': added_count,
                'validation': validation if current_size > 0 else None
            })

            # Safety check
            if iteration >= self.max_iterations:
                print(f"\n⚠️  Reached maximum iterations ({self.max_iterations})")
                break

        # Final validation
        print(f"\n{'=' * 80}")
        print("FINAL VALIDATION")
        print(f"{'=' * 80}")

        final_validation = await self._validate_deck(deck, deck_format)
        print(f"Final deck size: {len(deck)}")
        print(f"Valid: {final_validation['valid']}")
        print(f"Validations: {final_validation['validations']}")

        # Build result
        return {
            'deck': deck,
            'deck_size': len(deck),
            'valid': final_validation['valid'],
            'validation': final_validation,
            'iterations': iterations,
            'total_iterations': iteration
        }

    async def _fetch_cards_for_requirements(
        self,
        colors: List[str],
        archetype: str,
        deck_format: str,
        cards_needed: int,
        already_tried: set
    ) -> List[MTGCard]:
        """
        Fetch cards based on deck requirements

        Returns list of MTGCard objects
        """
        print(f"\nFetching cards for {archetype} deck...")

        # Define card search strategy based on archetype
        card_searches = self._get_card_search_strategy(
            colors=colors,
            archetype=archetype,
            cards_needed=cards_needed
        )

        fetched_cards = []

        for search_query in card_searches:
            # Skip if we've already tried this
            if search_query in already_tried:
                continue

            already_tried.add(search_query)

            # Use knowledge agent to extract and fetch
            response = await self.knowledge_agent.process({
                'query': search_query,
                'use_fuzzy': True
            })

            cards = [
                self._dict_to_card(c) for c in response.data.get('cards', [])
            ]

            fetched_cards.extend(cards)
            print(f"  Query: '{search_query}' → {len(cards)} cards")

            if len(fetched_cards) >= cards_needed:
                break

        return fetched_cards[:cards_needed]

    def _get_card_search_strategy(
        self,
        colors: List[str],
        archetype: str,
        cards_needed: int
    ) -> List[str]:
        """
        Generate card search queries based on archetype

        Returns list of search query strings
        """
        color_map = {
            'W': 'white', 'U': 'blue', 'B': 'black',
            'R': 'red', 'G': 'green'
        }

        color_names = [color_map.get(c, c) for c in colors]
        color_str = ' '.join(color_names)

        # Archetype-specific queries
        if archetype == 'aggro':
            # For aggro, we want creatures first, then burn, then lands
            creature_count = int(cards_needed * 0.4)  # 40% creatures
            spell_count = int(cards_needed * 0.3)     # 30% spells
            land_count = cards_needed - creature_count - spell_count  # 30% lands

            queries = []

            # Creatures
            if creature_count > 0:
                queries.extend([
                    f"Lightning Bolt, Goblin Guide, Monastery Swiftspear",
                    f"Eidolon of the Great Revel, Bomat Courier",
                    f"Soul-Scar Mage, Viashino Pyromancer"
                ])

            # Burn spells
            if spell_count > 0:
                queries.extend([
                    f"Lava Spike, Rift Bolt, Skewer the Critics",
                    f"Play with Fire, Shock"
                ])

            # Lands
            if land_count > 0:
                queries.append("Mountain")

            return queries

        elif archetype == 'control':
            queries = [
                f"Counterspell, Remove Soul, Cancel",
                f"Wrath of God, Day of Judgment",
                "Island"
            ]
            return queries

        elif archetype == 'midrange':
            queries = [
                f"Tarmogoyf, Siege Rhino",
                f"Lightning Bolt, Path to Exile"
            ]
            return queries

        # Default fallback
        return [f"{color_str} creature", f"{color_str} spell"]

    async def _validate_deck(
        self,
        deck: List[Dict[str, Any]],
        deck_format: str
    ) -> Dict[str, Any]:
        """
        Validate deck using symbolic reasoning agent

        Returns validation results
        """
        validation_response = await self.symbolic_agent.process({
            'type': 'deck_validation',
            'data': {
                'cards': deck,
                'format': deck_format
            }
        })

        return validation_response.data

    def _remove_illegal_cards(
        self,
        deck: List[Dict[str, Any]],
        deck_format: str,
        validation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Remove cards that are not legal in the format

        Returns cleaned deck list
        """
        legal_deck = []

        for card in deck:
            legalities = card.get('legalities', {})
            format_status = legalities.get(deck_format, 'not_legal')

            if format_status == 'legal':
                legal_deck.append(card)
            else:
                print(f"   Removing illegal: {card['name']} ({format_status} in {deck_format})")

        return legal_deck

    def _add_cards_to_deck(
        self,
        deck: List[Dict[str, Any]],
        new_cards: List[MTGCard],
        max_to_add: int
    ) -> int:
        """
        Add cards to deck, respecting 4-copy limit for non-basic lands

        Returns number of cards added
        """
        # Count existing cards
        card_counts = {}
        for card in deck:
            name = card['name']
            card_counts[name] = card_counts.get(name, 0) + 1

        added = 0

        for card in new_cards:
            if added >= max_to_add:
                break

            name = card.name
            current_count = card_counts.get(name, 0)

            # Check if it's a basic land
            is_basic = 'Basic Land' in card.type_line or name in ['Mountain', 'Island', 'Plains', 'Swamp', 'Forest']

            # Determine how many copies we can add
            if is_basic:
                copies_to_add = min(max_to_add - added, 4)  # Add up to 4 at a time
            else:
                max_allowed = 4
                copies_available = max_allowed - current_count
                copies_to_add = min(copies_available, max_to_add - added)

            # Add copies
            for _ in range(copies_to_add):
                deck.append(card.dict() if hasattr(card, 'dict') else card.model_dump())
                card_counts[name] = card_counts.get(name, 0) + 1
                added += 1

        return added

    def _dict_to_card(self, card_dict: Dict[str, Any]) -> MTGCard:
        """Convert dict to MTGCard object"""
        from ..models.card import CardColor, CardType

        # Handle colors
        colors = []
        for c in card_dict.get('colors', []):
            if isinstance(c, str):
                try:
                    colors.append(CardColor(c))
                except:
                    pass

        # Handle types
        types = []
        for t in card_dict.get('types', []):
            if isinstance(t, str):
                try:
                    types.append(CardType(t))
                except:
                    pass

        return MTGCard(
            id=card_dict['id'],
            name=card_dict['name'],
            mana_cost=card_dict.get('mana_cost'),
            cmc=card_dict.get('cmc', 0.0),
            colors=colors,
            color_identity=card_dict.get('color_identity', []),
            type_line=card_dict.get('type_line', ''),
            types=types,
            subtypes=card_dict.get('subtypes', []),
            oracle_text=card_dict.get('oracle_text'),
            power=card_dict.get('power'),
            toughness=card_dict.get('toughness'),
            loyalty=card_dict.get('loyalty'),
            set_code=card_dict.get('set_code', ''),
            rarity=card_dict.get('rarity', ''),
            legalities=card_dict.get('legalities', {}),
            keywords=card_dict.get('keywords', [])
        )
