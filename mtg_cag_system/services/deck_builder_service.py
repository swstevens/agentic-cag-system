"""
Iterative Deck Builder Service

This service coordinates agents to build a complete, legal deck through iteration:
1. Fetch initial cards based on requirements
2. Validate deck
3. If invalid, identify issues and fetch more/different cards
4. Repeat until deck is legal and complete
5. Analyze deck quality and apply recommendations (land ratio, mana curve, etc.)
"""

from typing import List, Dict, Any, Optional
from ..utils.deck_parser import DeckParser
from ..models.card import MTGCard
from ..agents.knowledge_fetch_agent import KnowledgeFetchAgent
from ..agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from .card_lookup_service import CardLookupService
from .deck_analyzer import DeckAnalyzer


class DeckBuilderService:
    """
    Iterative deck building service that produces complete, legal decks
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
        'EDH': 100,  # Alias for Commander
        'Brawl': 60,
        'Historic': 60,
        'Alchemy': 60,
        'Timeless': 60,
    }

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
        # Accept both 'strategy' and 'archetype' for compatibility
        archetype = requirements.get('strategy') or requirements.get('archetype', 'midrange')

        # Get format-specific deck size (exact requirement)
        target_size = self.FORMAT_DECK_SIZES.get(deck_format, 60)
        print(f"Target deck size for {deck_format}: {target_size} cards (exact)")

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

                # Check if deck is complete and legal (exact size required)
                if validation['valid'] and current_size == target_size:
                    print(f"\n✅ DECK COMPLETE AND LEGAL!")

                    # Analyze deck quality and apply recommendations
                    print(f"\n{'=' * 80}")
                    print("ANALYZING DECK QUALITY")
                    print(f"{'=' * 80}")
                    deck = await self._improve_deck_quality(deck, archetype, colors, deck_format, target_size)

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

        Args:
            colors: List of color identifiers (e.g. ['R', 'G'])
            archetype: Deck archetype/playstyle
            deck_format: Format legality to check (e.g. 'Standard')
            cards_needed: Number of cards to fetch
            already_tried: Set of card names already used

        Returns:
            List of MTGCard objects matching requirements
        """
        print(f"\nFetching cards for {archetype} deck...")

        # Get legal cards for format
        format_legality = {deck_format.lower(): "legal"}
        legal_cards = self.card_lookup._CardLookupService__database.search_cards(
            colors=colors,
            format_legality=format_legality,
            strict_colors=True,  # Only cards with exactly these colors (no multicolor)
            limit=1000  # High limit to get good coverage
        )
        print(f"Found {len(legal_cards)} legal cards for {deck_format} format")

        # Filter out already tried cards
        legal_cards = [c for c in legal_cards if c.name not in already_tried]
        print(f"Found {len(legal_cards)} untried cards")

        # Get archetype keywords
        archetype_keywords = self._get_archetype_keywords(archetype)

        # Score cards based on how well they match the archetype
        scored_cards = []
        for card in legal_cards:
            score = 0
            card_text = (card.oracle_text or "").lower()
            card_type = (card.type_line or "").lower()
            
            # Score based on archetype keywords
            for keyword in archetype_keywords:
                if keyword in card_text or keyword in card_type:
                    score += 1
            
            # Only include cards that match the archetype
            if score > 0:
                scored_cards.append((card, score))
                already_tried.add(card.name)

        # Sort by score descending
        scored_cards.sort(key=lambda x: x[1], reverse=True)
        
        # Take top matching cards
        fetched_cards = [card for card, score in scored_cards[:cards_needed]]
        print(f"Selected {len(fetched_cards)} cards matching {archetype} playstyle")
        
        return fetched_cards

    def _get_archetype_keywords(self, archetype: str) -> List[str]:
        """
        Get keywords that match a deck archetype's playstyle

        Args:
            archetype: The deck archetype (e.g. 'aggro', 'control', etc.)

        Returns:
            List of keywords that describe the archetype's playstyle
        """
        archetype = archetype.lower()
        
        if archetype == 'aggro':
            return [
                "haste", "attack", "damage", "combat",
                "aggressive", "fast", "burn", "strike",
                "prowess", "mentor", "blitz"
            ]
        elif archetype == 'control':
            return [
                "counter", "exile", "destroy", "return",
                "tap", "bounce", "draw", "removal",
                "board wipe", "counterspell"
            ]
        elif archetype == 'midrange':
            return [
                "value", "enters the battlefield", "token",
                "draw a card", "create", "gain", "put",
                "+1/+1", "trample", "ward"
            ]
        elif archetype == 'combo':
            return [
                "whenever", "trigger", "copy", "cast",
                "add mana", "untap", "activate",
                "sacrifice", "may", "instead"
            ]
        else:
            return []  # No specific keywords for unknown archetypes

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
        format_key = deck_format.lower()
        
        for card in deck:
            legalities = card.get('legalities', {})
            print(f"\nChecking legality for {card['name']}:")
            print(f"  Full legalities: {legalities}")
            
            # Get format status, defaulting to not_legal if not found
            status = legalities.get(format_key, 'not_legal').lower()
            print(f"  Status in {deck_format}: {status}")

            if status in ['legal', 'legal/gc', 'restricted']:
                legal_deck.append(card)
            else:
                print(f"   Removing illegal: {card['name']} ({status} in {deck_format})")
                print(f"   Full legalities: {legalities}")

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

    async def _improve_deck_quality(
        self,
        deck: List[Dict[str, Any]],
        archetype: str,
        colors: List[str],
        deck_format: str,
        target_size: int
    ) -> List[Dict[str, Any]]:
        """
        Analyze deck quality and apply recommendations from DeckAnalyzer
        Maintains exactly target_size cards by removing cards when adding lands

        Args:
            deck: Current deck list
            archetype: Deck archetype (aggro, control, midrange, combo)
            colors: Deck colors
            deck_format: Format (Standard, Modern, etc.)
            target_size: Exact deck size to maintain (60 for Standard, 100 for Commander, etc.)

        Returns:
            Improved deck list with exactly target_size cards
        """
        # Run deck analysis
        analysis = DeckAnalyzer.analyze_full_deck(deck, archetype)

        print(f"\nDeck Analysis Results:")
        print(f"  Overall Score: {analysis['overall_score']}/100")
        print(f"  Land Ratio: {analysis['land_ratio']['land_percentage']}% ({analysis['land_ratio']['ratio_quality']})")
        print(f"  Average CMC: {analysis['mana_curve']['average_cmc']:.2f}")
        print(f"  Recommendations: {len(analysis['recommendations'])}")

        for rec in analysis['recommendations']:
            print(f"    - {rec}")

        # Apply land ratio fixes while maintaining exact deck size
        land_ratio = analysis['land_ratio']
        mana_curve = analysis['mana_curve']

        if land_ratio['ratio_quality'] == 'too_few_lands':
            print(f"\n⚠️  Too few lands! Adding basic lands and removing cards...")
            deck = await self._add_basic_lands_and_remove_cards(
                deck, colors, land_ratio, mana_curve, deck_format, target_size
            )
        elif land_ratio['ratio_quality'] == 'too_many_lands':
            print(f"\n⚠️  Too many lands! Removing excess lands...")
            deck = self._remove_excess_lands(deck, land_ratio)

        # Re-analyze after improvements
        final_analysis = DeckAnalyzer.analyze_full_deck(deck, archetype)
        print(f"\nFinal Land Ratio: {final_analysis['land_ratio']['land_percentage']}% ({final_analysis['land_ratio']['ratio_quality']})")
        print(f"Final Score: {final_analysis['overall_score']}/100")

        return deck

    async def _add_basic_lands_and_remove_cards(
        self,
        deck: List[Dict[str, Any]],
        colors: List[str],
        land_ratio: Dict[str, Any],
        mana_curve: Dict[str, Any],
        deck_format: str,
        target_size: int
    ) -> List[Dict[str, Any]]:
        """
        Add appropriate basic lands to reach ideal land ratio
        Remove cards intelligently to maintain exact deck size

        Args:
            deck: Current deck
            colors: Deck colors
            land_ratio: Land ratio analysis from DeckAnalyzer
            mana_curve: Mana curve analysis from DeckAnalyzer
            deck_format: Format for validation
            target_size: Exact deck size to maintain

        Returns:
            Deck with improved land ratio and exactly target_size cards
        """
        # Calculate how many lands to add
        current_lands = land_ratio['land_count']
        ideal_min = land_ratio['ideal_percentage'][0] / 100
        target_lands = int(target_size * ideal_min)
        lands_to_add = max(0, target_lands - current_lands)

        print(f"  Current lands: {current_lands}")
        print(f"  Target lands: {target_lands}")
        print(f"  Lands to add: {lands_to_add}")

        if lands_to_add == 0:
            return deck

        # Step 1: Remove cards based on mana curve analysis
        print(f"\n  Removing {lands_to_add} cards to make room for lands...")
        deck = self._remove_cards_intelligently(deck, lands_to_add, mana_curve)
        print(f"  Deck size after removal: {len(deck)}")

        # Step 2: Add basic lands
        # Determine which basic land to add based on colors
        basic_land_map = {
            'W': 'Plains',
            'U': 'Island',
            'B': 'Swamp',
            'R': 'Mountain',
            'G': 'Forest'
        }

        # Get the appropriate basic land name
        if len(colors) == 0:
            # No colors specified - colorless deck, use Wastes
            basic_land_name = 'Wastes'
            print(f"  ℹ️  No colors specified, using {basic_land_name} for colorless deck")
        elif len(colors) == 1:
            # Mono-color: add that color's basic land
            color_code = self.card_lookup._CardLookupService__database._normalize_color(colors[0])
            basic_land_name = basic_land_map.get(color_code, 'Wastes')
        else:
            # Multi-color: distribute evenly or pick first color
            # TODO: Improve this to add multiple basic land types proportionally
            color_code = self.card_lookup._CardLookupService__database._normalize_color(colors[0])
            basic_land_name = basic_land_map.get(color_code, 'Wastes')

        # Fetch the basic land card
        basic_land = self.card_lookup._CardLookupService__database.get_card_by_name(basic_land_name)

        if basic_land:
            # Add the basic lands to the deck
            for _ in range(lands_to_add):
                deck.append(basic_land.dict() if hasattr(basic_land, 'dict') else basic_land.model_dump())
            print(f"  ✅ Added {lands_to_add}x {basic_land_name}")
            print(f"  Final deck size: {len(deck)} (target: {target_size})")
        else:
            print(f"  ❌ Could not find {basic_land_name} in database")

        return deck

    def _remove_cards_intelligently(
        self,
        deck: List[Dict[str, Any]],
        num_to_remove: int,
        mana_curve: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Remove cards based on mana curve analysis
        Prioritizes removing high CMC cards if curve is too high,
        or low impact cards if curve is good

        Args:
            deck: Current deck
            num_to_remove: Number of cards to remove
            mana_curve: Mana curve analysis

        Returns:
            Deck with cards removed
        """
        # Separate lands from non-lands
        lands = [c for c in deck if 'Land' in c.get('type_line', '')]
        nonlands = [c for c in deck if 'Land' not in c.get('type_line', '')]

        if len(nonlands) < num_to_remove:
            print(f"    ⚠️  Warning: Only {len(nonlands)} non-lands available to remove")
            num_to_remove = len(nonlands)

        # Determine removal strategy based on mana curve
        curve_quality = mana_curve.get('curve_quality', 'good')

        if curve_quality == 'too_high':
            # Remove highest CMC cards
            print(f"    Strategy: Removing highest CMC cards (curve too high)")
            nonlands.sort(key=lambda c: c.get('cmc', 0), reverse=True)
        elif curve_quality == 'too_low':
            # Remove lowest CMC cards (keep the high impact ones)
            print(f"    Strategy: Removing lowest CMC cards (curve too low)")
            nonlands.sort(key=lambda c: c.get('cmc', 0))
        else:
            # Remove highest CMC cards by default (more likely to be win-more)
            print(f"    Strategy: Removing highest CMC cards (default)")
            nonlands.sort(key=lambda c: c.get('cmc', 0), reverse=True)

        # Remove the cards
        cards_removed = nonlands[:num_to_remove]
        cards_kept = nonlands[num_to_remove:]

        for card in cards_removed:
            print(f"    - Removing: {card.get('name')} (CMC: {card.get('cmc', 0)})")

        # Return lands + kept cards
        return lands + cards_kept

    def _remove_excess_lands(
        self,
        deck: List[Dict[str, Any]],
        land_ratio: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Remove excess lands to reach ideal land ratio

        Args:
            deck: Current deck
            land_ratio: Land ratio analysis

        Returns:
            Deck with excess lands removed
        """
        # Calculate how many lands to remove
        current_lands = land_ratio['land_count']
        ideal_max = land_ratio['ideal_percentage'][1] / 100
        total_cards = len(deck)
        target_lands = int(total_cards * ideal_max)
        lands_to_remove = max(0, current_lands - target_lands)

        print(f"  Current lands: {current_lands}")
        print(f"  Target lands: {target_lands}")
        print(f"  Removing: {lands_to_remove} basic lands")

        if lands_to_remove == 0:
            return deck

        # Remove basic lands (prefer removing duplicates)
        lands_removed = 0
        new_deck = []

        for card in deck:
            is_basic_land = 'Basic Land' in card.get('type_line', '')
            if is_basic_land and lands_removed < lands_to_remove:
                lands_removed += 1
                continue
            new_deck.append(card)

        print(f"  ✅ Removed {lands_removed} basic lands")
        return new_deck
