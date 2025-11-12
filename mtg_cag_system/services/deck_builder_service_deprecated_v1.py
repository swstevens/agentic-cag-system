"""
Iterative Deck Builder Service

This service coordinates agents to build a complete, legal deck through iteration:
1. Fetch initial cards based on requirements
2. Validate deck
3. If invalid, identify issues and fetch more/different cards
4. Repeat until deck is legal and complete
5. Analyze deck quality and apply recommendations (land ratio, mana curve, etc.)
"""

import warnings
from typing import List, Dict, Any, Optional
from ..utils.deck_parser import DeckParser
from ..models.card import MTGCard
from ..agents.knowledge_fetch_agent import KnowledgeFetchAgent
from ..agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from ..agents.deck_analyzer_agent import DeckAnalyzerAgent
from .card_lookup_service import CardLookupService
from .deck_analyzer import DeckAnalyzer  # Legacy - deprecated


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
        analyzer_agent: Optional[DeckAnalyzerAgent] = None,
        max_iterations: int = 10
    ):
        """
        Initialize deck builder

        Args:
            knowledge_agent: Agent for fetching cards
            symbolic_agent: Agent for validation
            card_lookup: Direct card lookup service
            analyzer_agent: Optional DeckAnalyzerAgent for quality analysis.
                          If None, falls back to deprecated legacy DeckAnalyzer.
                          ⚠️  Providing DeckAnalyzerAgent is strongly recommended.
            max_iterations: Maximum iteration attempts
        """
        self.knowledge_agent = knowledge_agent
        self.symbolic_agent = symbolic_agent
        self.card_lookup = card_lookup
        self.analyzer_agent = analyzer_agent
        self.max_iterations = max_iterations

        # Warn if using legacy fallback
        if analyzer_agent is None:
            warnings.warn(
                "No DeckAnalyzerAgent provided to DeckBuilderService. "
                "Falling back to deprecated legacy DeckAnalyzer. "
                "Please provide a DeckAnalyzerAgent instance for better analysis. "
                "See ANALYZER_MIGRATION_GUIDE.md for migration instructions.",
                DeprecationWarning,
                stacklevel=2
            )

        # Protected deck state (initialized in build_deck)
        self._deck = []
        self._to_add = []

    # === Deck Access Methods ===

    def _get_deck(self) -> List[Dict[str, Any]]:
        """Get a copy of the current validated deck"""
        return self._deck.copy()

    def _get_deck_size(self) -> int:
        """Get the current size of the validated deck"""
        return len(self._deck)

    def _add_to_deck(self, cards: List[Dict[str, Any]]) -> None:
        """
        Add validated cards to the deck.
        Only use this after cards have been validated!

        Args:
            cards: List of validated card dictionaries
        """
        self._deck.extend(cards)

    def _get_to_add(self) -> List[Dict[str, Any]]:
        """Get a copy of the current candidate cards pending validation"""
        return self._to_add.copy()

    def _get_to_add_size(self) -> int:
        """Get the number of candidate cards pending validation"""
        return len(self._to_add)

    def _set_to_add(self, cards: List[Dict[str, Any]]) -> None:
        """
        Set the candidate cards list.
        These cards will be validated before being added to the deck.

        Args:
            cards: List of candidate card dictionaries
        """
        self._to_add = cards

    def _clear_to_add(self) -> None:
        """Clear the candidate cards list"""
        self._to_add = []

    def _reset_deck_state(self) -> None:
        """Reset the deck state for a new build"""
        self._deck = []
        self._to_add = []

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

        # Reset deck state for new build
        self._reset_deck_state()
        card_names_tried = set()
        iterations = []

        # Iteration loop
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'=' * 80}")
            print(f"ITERATION {iteration}")
            print(f"{'=' * 80}")

            # Step 1: Assess current deck state
            current_size = self._get_deck_size()
            print(f"Current deck size: {current_size}/{target_size}")
            print(f"Candidate cards to validate: {self._get_to_add_size()}")

            # Step 2: Validate candidate cards (if any)
            if self._get_to_add_size() > 0:
                print(f"\n{'=' * 80}")
                print("VALIDATING CANDIDATE CARDS")
                print(f"{'=' * 80}")

                validation_result = DeckAnalyzer.validate_candidate_cards(
                    candidate_cards=self._get_to_add(),
                    current_deck=self._get_deck(),
                    deck_format=deck_format
                )

                print(f"Valid cards: {validation_result['num_valid']}")
                print(f"Invalid cards: {validation_result['num_invalid']}")

                if validation_result['issues']:
                    print("\nIssues found:")
                    for issue in validation_result['issues']:
                        print(f"  - {issue}")

                # Move valid cards from to_add to deck
                valid_cards = validation_result['valid_cards']
                self._add_to_deck(valid_cards)
                print(f"\n✅ Added {len(valid_cards)} validated cards to deck")
                print(f"New deck size: {self._get_deck_size()}/{target_size}")

                # Clear to_add list
                self._clear_to_add()

            # Step 3: Check if deck is complete
            if self._get_deck_size() == target_size:
                print(f"\n✅ DECK COMPLETE!")

                # Analyze deck quality and apply recommendations
                print(f"\n{'=' * 80}")
                print("ANALYZING DECK QUALITY")
                print(f"{'=' * 80}")
                await self._improve_deck_quality(archetype, colors, deck_format, target_size)

                break

            # Step 4: Determine what cards are needed
            cards_needed = target_size - self._get_deck_size()
            print(f"\nCards needed: {cards_needed}")

            if cards_needed <= 0:
                continue

            # Step 5: Fetch new candidate cards based on requirements
            new_cards = await self._fetch_cards_for_requirements(
                colors=colors,
                archetype=archetype,
                deck_format=deck_format,
                cards_needed=cards_needed,
                already_tried=card_names_tried
            )

            # Step 6: Add fetched cards to to_add list (will be validated next iteration)
            candidate_cards = self._prepare_candidate_cards(new_cards, cards_needed)
            self._set_to_add(candidate_cards)
            print(f"Prepared {self._get_to_add_size()} candidate cards for validation")

            # Track iteration
            iterations.append({
                'iteration': iteration,
                'deck_size': self._get_deck_size(),
                'candidates_prepared': self._get_to_add_size(),
                'cards_needed': cards_needed
            })

            # Safety check
            if iteration >= self.max_iterations:
                print(f"\n⚠️  Reached maximum iterations ({self.max_iterations})")
                break

        # Final status
        print(f"\n{'=' * 80}")
        print("FINAL DECK STATUS")
        print(f"{'=' * 80}")
        print(f"Final deck size: {self._get_deck_size()}/{target_size}")

        is_valid = self._get_deck_size() == target_size
        print(f"Valid: {is_valid}")

        # Build result
        final_deck = self._get_deck()
        return {
            'deck': final_deck,
            'deck_size': len(final_deck),
            'valid': is_valid,
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
            strict_colors=False,  # Allow cards in any of these colors, not just exactly these colors
            limit=2000  # Higher limit to get better coverage for deck building
        )
        print(f"Found {len(legal_cards)} legal cards for {deck_format} format")

        # Filter out already tried cards
        legal_cards = [c for c in legal_cards if c.name not in already_tried]
        print(f"Found {len(legal_cards)} untried cards")

        # Get archetype keywords
        archetype_keywords = self._get_archetype_keywords(archetype)

        # Score cards based on how well they match the archetype
        scored_cards = []
        basic_lands = []

        for card in legal_cards:
            card_type = (card.type_line or "").lower()

            # Separate basic lands from other cards
            # Check for basic lands by type line or known land names
            is_basic_land = (
                'basic land' in card_type or
                card.name in ['Mountain', 'Island', 'Plains', 'Swamp', 'Forest', 'Wastes'] or
                card_type in ['land', 'basic land — mountain', 'basic land — island', 'basic land — plains', 'basic land — swamp', 'basic land — forest']
            )

            if is_basic_land:
                basic_lands.append(card)
            else:
                score = 0
                card_text = (card.oracle_text or "").lower()

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

        # Calculate how many lands vs non-lands to include
        # Use archetype-specific land ratios from DeckAnalyzer
        arch_data = DeckAnalyzer.ARCHETYPE_CURVES.get(archetype.lower(), DeckAnalyzer.ARCHETYPE_CURVES['midrange'])
        ideal_land_ratio = sum(arch_data['land_ratio']) / 2  # Average of min/max

        estimated_lands_needed = int(cards_needed * ideal_land_ratio)
        estimated_nonlands_needed = cards_needed - estimated_lands_needed

        # Take top matching non-land cards
        nonland_cards = [card for card, score in scored_cards[:estimated_nonlands_needed]]

        # Distribute basic lands across deck colors
        land_cards = self._distribute_lands_by_color(colors, basic_lands, estimated_lands_needed)

        # Combine non-lands and lands
        fetched_cards = nonland_cards + land_cards

        # Print summary with color breakdown for multi-color decks
        if len(colors) > 1:
            land_counts = {}
            for land in land_cards:
                land_name = land.name
                land_counts[land_name] = land_counts.get(land_name, 0) + 1
            land_summary = ", ".join([f"{count}x {name}" for name, count in land_counts.items()])
            print(f"Selected {len(nonland_cards)} non-land cards and {len(land_cards)} lands ({land_summary})")
        else:
            print(f"Selected {len(nonland_cards)} non-land cards and {len(land_cards)} lands matching {archetype} playstyle")

        return fetched_cards

    def _distribute_lands_by_color(
        self,
        colors: List[str],
        basic_lands: List[MTGCard],
        total_lands_needed: int
    ) -> List[MTGCard]:
        """
        Distribute basic lands proportionally across deck colors.
        For multi-color decks, splits lands evenly between colors.

        Args:
            colors: List of color codes (e.g., ['R', 'G'])
            basic_lands: Available basic land cards
            total_lands_needed: Total number of lands to include

        Returns:
            List of land cards distributed across colors
        """
        if len(colors) == 0 or total_lands_needed == 0:
            return []

        # Normalize colors to single-letter codes
        normalized_colors = []
        for color in colors:
            normalized_color = self.card_lookup._CardLookupService__database._normalize_color(color)
            normalized_colors.append(normalized_color)

        print(f"    DEBUG: Original colors: {colors}, Normalized: {normalized_colors}, Total lands needed: {total_lands_needed}")
        print(f"    DEBUG: Available basic lands: {len(basic_lands)}")

        basic_land_map = {
            'W': 'Plains',
            'U': 'Island',
            'B': 'Swamp',
            'R': 'Mountain',
            'G': 'Forest'
        }

        land_cards = []

        if len(normalized_colors) == 1:
            # Mono-color: all lands of one type
            color_code = normalized_colors[0]
            basic_land_name = basic_land_map.get(color_code, 'Mountain')
            matching_lands = [land for land in basic_lands if land.name == basic_land_name]

            print(f"    DEBUG: Mono-color - Looking for {basic_land_name}, found {len(matching_lands)} matches")

            if matching_lands:
                land_cards = matching_lands[:1] * total_lands_needed
            else:
                # Fallback: use any land available or create placeholder
                if basic_lands:
                    land_cards = basic_lands[:1] * total_lands_needed
                    print(f"    DEBUG: Using fallback land {basic_lands[0].name} instead")
        else:
            # Multi-color: distribute evenly
            lands_per_color = total_lands_needed // len(normalized_colors)
            remainder = total_lands_needed % len(normalized_colors)

            print(f"    DEBUG: Multi-color - {lands_per_color} per color, {remainder} remainder")

            for i, color_code in enumerate(normalized_colors):
                basic_land_name = basic_land_map.get(color_code, 'Mountain')
                matching_lands = [land for land in basic_lands if land.name == basic_land_name]

                print(f"    DEBUG: Color {color_code} -> {basic_land_name}, found {len(matching_lands)} matches")

                if matching_lands:
                    # Give the first color(s) one extra land if there's a remainder
                    lands_for_this_color = lands_per_color + (1 if i < remainder else 0)
                    land_cards.extend(matching_lands[:1] * lands_for_this_color)
                    print(f"    DEBUG: Adding {lands_for_this_color}x {basic_land_name}")
                elif basic_lands:
                    # Fallback: use any available land for this color
                    lands_for_this_color = lands_per_color + (1 if i < remainder else 0)
                    land_cards.extend(basic_lands[:1] * lands_for_this_color)
                    print(f"    DEBUG: Using fallback land {basic_lands[0].name} for {color_code}")

        print(f"    DEBUG: Total land cards returned: {len(land_cards)}")
        return land_cards

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

    def _prepare_candidate_cards(
        self,
        new_cards: List[MTGCard],
        max_to_add: int
    ) -> List[Dict[str, Any]]:
        """
        Prepare candidate cards for validation by converting to dict format.
        Does NOT validate or add to deck - just prepares them for the to_add list.

        Args:
            new_cards: List of MTGCard objects from fetch
            max_to_add: Maximum number of cards to prepare

        Returns:
            List of card dictionaries ready for validation
        """
        prepared = []

        for card in new_cards[:max_to_add]:
            card_dict = card.dict() if hasattr(card, 'dict') else card.model_dump()
            prepared.append(card_dict)

        return prepared

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
        archetype: str,
        colors: List[str],
        deck_format: str,
        target_size: int
    ) -> None:
        """
        Analyze deck quality and apply recommendations from DeckAnalyzerAgent
        Maintains exactly target_size cards by removing cards when adding lands
        Modifies the protected _deck directly.

        Args:
            archetype: Deck archetype (aggro, control, midrange, combo)
            colors: Deck colors
            deck_format: Format (Standard, Modern, etc.)
            target_size: Exact deck size to maintain (60 for Standard, 100 for Commander, etc.)
        """
        # Run deck analysis using agent or fallback to legacy analyzer
        if self.analyzer_agent:
            print("\n🤖 Using DeckAnalyzerAgent (LLM-based analysis)...")
            analysis = await self.analyzer_agent.analyze_full_deck(
                cards=self._get_deck(),
                archetype=archetype,
                deck_format=deck_format,
                deck_size=target_size
            )
        else:
            print("\n📊 Using legacy DeckAnalyzer (rule-based analysis)...")
            analysis = DeckAnalyzer.analyze_full_deck(self._get_deck(), archetype)

        print(f"\nDeck Analysis Results:")
        print(f"  Overall Score: {analysis['overall_score']}/100")

        # Handle both new agent format and old format
        if 'land_ratio' in analysis:
            land_ratio = analysis['land_ratio']
            if isinstance(land_ratio, dict):
                land_pct = land_ratio.get('land_percentage', 0)
                ratio_quality = land_ratio.get('ratio_quality', 'unknown')
            else:
                # New format from DeckAnalyzerAgent
                land_pct = land_ratio.land_percentage if hasattr(land_ratio, 'land_percentage') else 0
                ratio_quality = land_ratio.ratio_quality if hasattr(land_ratio, 'ratio_quality') else 'unknown'
            print(f"  Land Ratio: {land_pct}% ({ratio_quality})")

        if 'mana_curve' in analysis:
            mana_curve = analysis['mana_curve']
            if isinstance(mana_curve, dict):
                avg_cmc = mana_curve.get('average_cmc', 0)
            else:
                avg_cmc = mana_curve.average_cmc if hasattr(mana_curve, 'average_cmc') else 0
            print(f"  Average CMC: {avg_cmc:.2f}")

        # Print priority improvements if using new agent
        if 'priority_improvements' in analysis:
            priority_improvements = analysis.get('priority_improvements', [])
            if priority_improvements:
                print(f"  Priority Improvements:")
                for imp in priority_improvements[:5]:  # Top 5
                    print(f"    - {imp}")
        elif 'recommendations' in analysis:
            # Legacy format
            recommendations = analysis.get('recommendations', [])
            if recommendations:
                print(f"  Recommendations: {len(recommendations)}")
                for rec in recommendations:
                    print(f"    - {rec}")

        # Apply land ratio fixes while maintaining exact deck size
        # Convert to dict format for backward compatibility with helper methods
        if 'land_ratio' in analysis:
            land_ratio_dict = self._normalize_land_ratio(analysis['land_ratio'])
            mana_curve_dict = self._normalize_mana_curve(analysis['mana_curve'])

            ratio_quality = land_ratio_dict.get('ratio_quality', 'good')

            if 'too_few' in ratio_quality.lower():
                print(f"\n⚠️  Too few lands! Adding basic lands and removing cards...")
                await self._add_basic_lands_and_remove_cards(
                    colors, land_ratio_dict, mana_curve_dict, deck_format, target_size
                )
            elif 'too_many' in ratio_quality.lower():
                print(f"\n⚠️  Too many lands! Removing excess lands...")
                self._remove_excess_lands(land_ratio_dict)

            # Re-analyze after improvements
            if self.analyzer_agent:
                final_analysis = await self.analyzer_agent.analyze_full_deck(
                    cards=self._get_deck(),
                    archetype=archetype,
                    deck_format=deck_format,
                    deck_size=target_size
                )
            else:
                final_analysis = DeckAnalyzer.analyze_full_deck(self._get_deck(), archetype)

            final_land_ratio = self._normalize_land_ratio(final_analysis['land_ratio'])
            print(f"\nFinal Land Ratio: {final_land_ratio['land_percentage']}% ({final_land_ratio['ratio_quality']})")
            print(f"Final Score: {final_analysis['overall_score']}/100")

    def _normalize_land_ratio(self, land_ratio: Any) -> Dict[str, Any]:
        """Convert land_ratio to dict format for backward compatibility"""
        if isinstance(land_ratio, dict):
            return land_ratio
        # Convert Pydantic model to dict
        return {
            'land_count': land_ratio.land_count,
            'land_percentage': land_ratio.land_percentage,
            'ratio_quality': land_ratio.ratio_quality,
            'recommended_land_count': land_ratio.recommended_land_count,
            'ideal_percentage': (35.0, 45.0) if land_ratio.recommended_land_count else (38.0, 45.0)
        }

    def _normalize_mana_curve(self, mana_curve: Any) -> Dict[str, Any]:
        """Convert mana_curve to dict format for backward compatibility"""
        if isinstance(mana_curve, dict):
            return mana_curve
        # Convert Pydantic model to dict
        return {
            'average_cmc': mana_curve.average_cmc,
            'curve_quality': mana_curve.curve_quality,
            'curve': mana_curve.curve_distribution if hasattr(mana_curve, 'curve_distribution') else {}
        }

    async def _add_basic_lands_and_remove_cards(
        self,
        colors: List[str],
        land_ratio: Dict[str, Any],
        mana_curve: Dict[str, Any],
        deck_format: str,
        target_size: int
    ) -> None:
        """
        Add appropriate basic lands to reach ideal land ratio
        Remove cards intelligently to maintain exact deck size
        Modifies the protected _deck directly.

        Args:
            colors: Deck colors
            land_ratio: Land ratio analysis from DeckAnalyzer
            mana_curve: Mana curve analysis from DeckAnalyzer
            deck_format: Format for validation
            target_size: Exact deck size to maintain
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
            return

        # Step 1: Remove cards based on mana curve analysis
        print(f"\n  Removing {lands_to_add} cards to make room for lands...")
        self._remove_cards_intelligently(lands_to_add, mana_curve)
        print(f"  Deck size after removal: {self._get_deck_size()}")

        # Step 2: Add basic lands distributed across colors
        basic_land_map = {
            'W': 'Plains',
            'U': 'Island',
            'B': 'Swamp',
            'R': 'Mountain',
            'G': 'Forest'
        }

        lands_to_add_list = []

        if len(colors) == 0:
            # No colors specified - colorless deck, use Wastes
            basic_land_name = 'Wastes'
            print(f"  ℹ️  No colors specified, using {basic_land_name} for colorless deck")
            basic_land = self.card_lookup._CardLookupService__database.get_card_by_name(basic_land_name)
            if basic_land:
                for _ in range(lands_to_add):
                    lands_to_add_list.append(basic_land.dict() if hasattr(basic_land, 'dict') else basic_land.model_dump())
        elif len(colors) == 1:
            # Mono-color: add that color's basic land
            color_code = self.card_lookup._CardLookupService__database._normalize_color(colors[0])
            basic_land_name = basic_land_map.get(color_code, 'Wastes')
            basic_land = self.card_lookup._CardLookupService__database.get_card_by_name(basic_land_name)
            if basic_land:
                for _ in range(lands_to_add):
                    lands_to_add_list.append(basic_land.dict() if hasattr(basic_land, 'dict') else basic_land.model_dump())
                print(f"  ✅ Adding {lands_to_add}x {basic_land_name}")
        else:
            # Multi-color: distribute evenly across colors
            lands_per_color = lands_to_add // len(colors)
            remainder = lands_to_add % len(colors)

            land_distribution = {}
            for i, color in enumerate(colors):
                color_code = self.card_lookup._CardLookupService__database._normalize_color(color)
                basic_land_name = basic_land_map.get(color_code, 'Mountain')
                basic_land = self.card_lookup._CardLookupService__database.get_card_by_name(basic_land_name)

                if basic_land:
                    # Give the first color(s) one extra land if there's a remainder
                    lands_for_this_color = lands_per_color + (1 if i < remainder else 0)
                    land_distribution[basic_land_name] = lands_for_this_color

                    for _ in range(lands_for_this_color):
                        lands_to_add_list.append(basic_land.dict() if hasattr(basic_land, 'dict') else basic_land.model_dump())

            # Print multi-color land distribution
            land_summary = ", ".join([f"{count}x {name}" for name, count in land_distribution.items()])
            print(f"  ✅ Adding {lands_to_add} lands distributed as: {land_summary}")

        # Add all lands to the deck
        if lands_to_add_list:
            self._add_to_deck(lands_to_add_list)
            print(f"  Final deck size: {self._get_deck_size()} (target: {target_size})")
        else:
            print(f"  ❌ Could not find basic lands in database")

    def _remove_cards_intelligently(
        self,
        num_to_remove: int,
        mana_curve: Dict[str, Any]
    ) -> None:
        """
        Remove cards based on mana curve analysis
        Prioritizes removing high CMC cards if curve is too high,
        or low impact cards if curve is good
        Modifies the protected _deck directly.

        Args:
            num_to_remove: Number of cards to remove
            mana_curve: Mana curve analysis
        """
        # Separate lands from non-lands
        deck = self._get_deck()
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

        # Update the deck with lands + kept cards
        self._deck = lands + cards_kept

    def _remove_excess_lands(
        self,
        land_ratio: Dict[str, Any]
    ) -> None:
        """
        Remove excess lands to reach ideal land ratio
        Modifies the protected _deck directly.

        Args:
            land_ratio: Land ratio analysis
        """
        # Calculate how many lands to remove
        current_lands = land_ratio['land_count']
        ideal_max = land_ratio['ideal_percentage'][1] / 100
        total_cards = self._get_deck_size()
        target_lands = int(total_cards * ideal_max)
        lands_to_remove = max(0, current_lands - target_lands)

        print(f"  Current lands: {current_lands}")
        print(f"  Target lands: {target_lands}")
        print(f"  Removing: {lands_to_remove} basic lands")

        if lands_to_remove == 0:
            return

        # Remove basic lands (prefer removing duplicates)
        lands_removed = 0
        new_deck = []

        for card in self._get_deck():
            is_basic_land = 'Basic Land' in card.get('type_line', '')
            if is_basic_land and lands_removed < lands_to_remove:
                lands_removed += 1
                continue
            new_deck.append(card)

        print(f"  ✅ Removed {lands_removed} basic lands")
        self._deck = new_deck
