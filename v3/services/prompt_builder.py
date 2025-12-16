"""
Dynamic prompt builder for LLM agents.

Generates format-aware, context-specific prompts for deck building
and refinement agents using FormatRules configuration.
"""

from typing import Dict, List
from ..models.format_rules import FormatRules


class PromptBuilder:
    """
    Builds dynamic prompts for LLM agents based on format rules.

    This ensures prompts are always accurate and format-specific,
    pulling data directly from the FormatRules configuration.
    """

    @staticmethod
    def build_deck_builder_system_prompt(format_name: str = "Standard") -> str:
        """
        Generate format-aware system prompt for deck building agent.

        Args:
            format_name: Format to build deck for

        Returns:
            System prompt string with format-specific guidelines
        """
        rules = FormatRules.get_rules(format_name)
        is_singleton = rules["singleton_rule"]
        deck_size = rules["deck_size_max"]
        copy_limit = rules["copy_limit"]
        legendary_max = rules["legendary_max"]

        # Get archetype land counts for this format
        archetype_lands = FormatRules.ARCHETYPE_LAND_COUNTS.get(format_name, {})

        # Get mana curve standards
        curve_standards = FormatRules.get_mana_curve_standards(format_name)

        # Build format-specific section
        format_section = PromptBuilder._build_format_guidelines(
            format_name, deck_size, is_singleton, copy_limit
        )

        # Build archetype section
        archetype_section = PromptBuilder._build_archetype_guidelines(
            format_name, archetype_lands, deck_size, is_singleton
        )

        # Build mana curve section
        curve_section = PromptBuilder._build_mana_curve_guidelines(
            format_name, curve_standards
        )

        # Build card quantity rules section
        quantity_section = PromptBuilder._build_quantity_rules(
            is_singleton, copy_limit, legendary_max
        )

        prompt = f"""You are an expert Magic: The Gathering deck builder.

Your goal is to construct competitive decks by intelligently selecting cards
that work well together and fit the requested archetype.

{format_section}

{archetype_section}

{curve_section}

DECK COMPOSITION (for {deck_size}-card decks):
- Threats: {PromptBuilder._get_threat_range(deck_size)} cards (creatures or win conditions)
- Removal: {PromptBuilder._get_removal_range(deck_size)} cards (spot removal, sweepers)
- Card Draw: {PromptBuilder._get_draw_range(deck_size)} cards (cantrips, draw spells)
- Utility: {PromptBuilder._get_utility_range(deck_size)} cards (ramp, protection, disruption)

CARD SELECTION STRATEGY:
1. Use 'semantic_query' for conceptual searches:
   - "aggressive one-drop creatures" instead of types=["Creature"], cmc_max=1
   - "removal that exiles" instead of text_query="exile"
   - "card draw engines" instead of text_query="draw"
2. Use filters for hard constraints:
   - colors: Match deck color identity (e.g., ["R", "W"] for Boros)
   - cmc_min/cmc_max: Filter by converted mana cost
   - types: Filter by card type when critical
3. Build for CONSISTENCY:
   {PromptBuilder._get_consistency_guidance(is_singleton)}

{quantity_section}

For each card selection, provide clear reasoning about:
- What role it fills (removal, threat, draw, etc.)
- How it synergizes with other cards
- Why it fits the archetype strategy

You have access to tools to search the card database. Use them strategically to find cards
that match the deck's strategy and format requirements.
"""

        return prompt

    @staticmethod
    def build_refine_agent_system_prompt(format_name: str = "Standard") -> str:
        """
        Generate format-aware system prompt for deck refinement agent.

        Args:
            format_name: Format to refine deck for

        Returns:
            System prompt string with format-specific refinement guidelines
        """
        rules = FormatRules.get_rules(format_name)
        is_singleton = rules["singleton_rule"]
        deck_size = rules["deck_size_max"]
        copy_limit = rules["copy_limit"]
        legendary_max = rules["legendary_max"]

        # Get mana curve standards
        curve_standards = FormatRules.get_mana_curve_standards(format_name)
        curve_guidance = PromptBuilder._format_curve_targets(curve_standards)

        # Build card quantity rules section
        quantity_section = PromptBuilder._build_quantity_rules(
            is_singleton, copy_limit, legendary_max
        )

        prompt = f"""You are an expert Magic: The Gathering deck optimizer.

Your goal is to improve existing decks by identifying weaknesses and
making targeted, high-impact improvements.

ANALYSIS FRAMEWORK FOR {format_name} ({deck_size}-card format):

1. **Mana Curve Issues**:
   - Too many high-cost cards → Clunky hands, slow starts
   - Too many low-cost cards → Runs out of gas, weak late game
   - Target curve for {format_name}:
{curve_guidance}

2. **Synergy Problems**:
   - Cards that don't support the deck's strategy
   - Missing key combo pieces or enablers
   - Lack of tribal/keyword overlap

3. **Consistency Issues**:
   {"- Too many unique cards (singleton requires redundant effects across different cards)" if is_singleton else "- Too many 1-ofs (hard to find when needed)"}
   {"- Missing redundancy for critical effects" if is_singleton else "- Missing redundancy for critical effects"}
   - Legendary cards with {legendary_max + 1}+ copies (dead cards in hand)

4. **Interaction Gaps**:
   - No removal for problematic permanents
   - No counterspells/protection for combo pieces
   - No card draw to maintain resources

5. **Win Condition Clarity**:
   - Unclear how the deck wins
   - Too many finishers (dilutes consistency)
   - Not enough finishers (can't close games)

REFINEMENT STRATEGY:
1. Identify the deck's PRIMARY win condition
2. Remove cards that don't support that win condition
3. Add cards that enable/protect the win condition
4. Ensure proper curve, interaction, and draw

{quantity_section}

DECK SIZE CONSTRAINTS:
- Target deck size: {deck_size} cards
- If current < target: Add more than you remove
- If current > target: Remove more than you add
- If current == target: Equal adds/removes

Be specific and strategic. Focus on high-impact changes that address
the most critical weaknesses first. Use search_cards_refine to find
better alternatives (semantic_query works best).
"""

        return prompt

    @staticmethod
    def build_llm_analyzer_system_prompt(format_name: str = "Standard") -> str:
        """
        Generate format-aware system prompt for LLM deck analyzer.

        Args:
            format_name: Format to analyze deck for

        Returns:
            System prompt string with format-specific analysis guidelines
        """
        rules = FormatRules.get_rules(format_name)
        is_singleton = rules["singleton_rule"]
        deck_size = rules["deck_size_max"]
        copy_limit = rules["copy_limit"]

        # Get mana curve standards
        curve_standards = FormatRules.get_mana_curve_standards(format_name)
        curve_guidance = PromptBuilder._format_curve_targets(curve_standards)

        prompt = f"""You are an expert Magic: The Gathering deck builder and analyzer.

Your goal is to analyze a given deck and provide a concrete, actionable improvement plan.
You must identify weak cards to remove and suggest specific, better replacements.

ANALYSIS PRIORITIES FOR {format_name} ({deck_size}-card format):
1. **Deck Size & Format Compliance**: Ensure exactly {deck_size} cards and legal in {format_name}
2. **Mana Curve Optimization**:
{curve_guidance}
3. **Win Conditions**: Clear, consistent path to victory
4. **Interaction/Removal**: Ability to deal with opponent's threats
5. **Synergy & Consistency**: Cards work together and appear reliably
6. **Card Advantage**: Sufficient draw/filtering to maintain resources

ARCHETYPE-SPECIFIC ANALYSIS:
- **Aggro**: Enough 1-2 CMC threats? Is there reach (burn/direct damage)? Too many lands?
- **Midrange**: Card advantage? Versatile removal? Efficient threats at multiple CMC points?
- **Control**: Enough removal/counterspells? Clear finishers? Too few lands?
- **Combo**: Combo pieces present in sufficient redundancy? Protection and tutoring?

QUALITY STANDARDS FOR RECOMMENDATIONS:
✅ GOOD removal reasoning: "Remove 2x [Card Name] - This 5-mana removal spell is too slow for aggro; you need 1-2 mana interaction"
❌ BAD removal reasoning: "Remove [Card Name] - It's not good"

✅ GOOD addition reasoning: "Add 4x Lightning Bolt - Efficient 1-mana removal that doubles as reach to close games"
❌ BAD addition reasoning: "Add Lightning Bolt - Good removal spell"

CONSTRAINTS:
- Only recommend cards that exist in Magic: The Gathering
- Respect {format_name} legality
- Maintain deck's color identity (don't suggest off-color cards)
{"- SINGLETON FORMAT: Maximum 1 copy per card (except basic lands)" if is_singleton else f"- Maximum {copy_limit} copies per non-basic-land card"}

OUTPUT FORMAT:
- Provide 2-5 removals (focus on weakest cards)
- Provide 2-5 additions (focus on highest-impact replacements)
- Include clear, specific reasoning for each change
- Explain how changes improve the deck's overall strategy
"""

        return prompt

    # Helper methods

    @staticmethod
    def _build_format_guidelines(format_name: str, deck_size: int, is_singleton: bool, copy_limit: int) -> str:
        """Build format-specific guidelines section."""
        singleton_note = "- SINGLETON FORMAT: Exactly 1 copy of each non-basic-land card" if is_singleton else f"- Maximum {copy_limit} copies per card (except basic lands)"

        return f"""FORMAT: {format_name} ({deck_size} cards)
{singleton_note}
- Focus on {'redundant effects across different cards' if is_singleton else f'{copy_limit}-ofs for key cards'}"""

    @staticmethod
    def _build_archetype_guidelines(format_name: str, archetype_lands: Dict[str, int], deck_size: int, is_singleton: bool) -> str:
        """Build archetype-specific guidelines section."""
        if not archetype_lands:
            return "ARCHETYPE GUIDELINES:\n- Refer to general deck building principles"

        lines = ["ARCHETYPE GUIDELINES:"]

        for archetype, land_count in archetype_lands.items():
            spell_count = deck_size - land_count

            if archetype.lower() == "aggro":
                lines.append(f"- {archetype}: Low curve (1-3 CMC), {PromptBuilder._get_threat_range_for_archetype(deck_size, 'aggro')} efficient creatures, {land_count} lands")
                lines.append(f"  * Focus: Early pressure, combat tricks, reach (burn/direct damage)")
            elif archetype.lower() == "midrange":
                lines.append(f"- {archetype}: Balanced curve (2-5 CMC), value cards, {spell_count} spells, {land_count} lands")
                lines.append(f"  * Focus: Card advantage, versatile removal, efficient threats")
            elif archetype.lower() == "control":
                lines.append(f"- {archetype}: Higher curve (3-6 CMC), {PromptBuilder._get_control_spell_distribution(spell_count)}, {land_count} lands")
                lines.append(f"  * Focus: Removal, counterspells, card draw, sweepers, late-game finishers")
            elif archetype.lower() == "combo":
                combo_dist = PromptBuilder._get_combo_spell_distribution(spell_count)
                lines.append(f"- {archetype}: Focused curve based on combo pieces, {spell_count} spells, {land_count} lands")
                lines.append(f"  * Focus: {combo_dist}")

        return "\n".join(lines)

    @staticmethod
    def _build_mana_curve_guidelines(format_name: str, curve_standards: Dict[str, float]) -> str:
        """Build mana curve guidelines section."""
        lines = [f"MANA CURVE TARGETS FOR {format_name}:"]

        for cmc_range, percentage in curve_standards.items():
            lines.append(f"- {cmc_range} CMC: ~{int(percentage * 100)}% of spells")

        return "\n".join(lines)

    @staticmethod
    def _build_quantity_rules(is_singleton: bool, copy_limit: int, legendary_max: int) -> str:
        """Build card quantity rules section."""
        if is_singleton:
            return """CARD QUANTITY RULES (SINGLETON FORMAT):
- All non-basic-land cards: EXACTLY 1 copy
- Basic lands: Unlimited copies allowed
- Focus on redundancy through SIMILAR effects, not duplicate cards
- Example: Multiple different card draw spells rather than 4x of one"""
        else:
            return f"""CARD QUANTITY RULES:
- **Legendary cards**: Maximum {legendary_max} copies (legendary rule: only 1 on battlefield)
  * Typically include 2-3 copies for consistency/redundancy
- **Non-legendary cards**: Maximum {copy_limit} copies
  * 4-ofs: Critical cards you want every game
  * 3-ofs: Strong cards you want frequently
  * 2-ofs: Good cards or situational pieces
  * 1-ofs: Avoid unless legendary, highly situational, or tutored for
- **Basic lands**: Unlimited copies allowed"""

    @staticmethod
    def _get_consistency_guidance(is_singleton: bool) -> str:
        """Get consistency guidance based on format."""
        if is_singleton:
            return "- Singleton formats: Focus on redundant EFFECTS (multiple card draw sources, multiple removal types)"
        else:
            return "- 60-card formats: Use 3-4 copies of your best cards for consistency"

    @staticmethod
    def _format_curve_targets(curve_standards: Dict[str, float]) -> str:
        """Format mana curve targets as indented list."""
        lines = []
        for cmc_range, percentage in curve_standards.items():
            lines.append(f"     * {cmc_range} CMC: ~{int(percentage * 100)}% of nonland cards")
        return "\n".join(lines)

    @staticmethod
    def _get_threat_range(deck_size: int) -> str:
        """Get threat card range based on deck size."""
        if deck_size == 100:
            return "20-30"
        else:
            return "12-20"

    @staticmethod
    def _get_removal_range(deck_size: int) -> str:
        """Get removal card range based on deck size."""
        if deck_size == 100:
            return "10-15"
        else:
            return "6-12"

    @staticmethod
    def _get_draw_range(deck_size: int) -> str:
        """Get card draw range based on deck size."""
        if deck_size == 100:
            return "10-15"
        else:
            return "4-8"

    @staticmethod
    def _get_utility_range(deck_size: int) -> str:
        """Get utility card range based on deck size."""
        if deck_size == 100:
            return "5-15"
        else:
            return "0-8"

    @staticmethod
    def _get_threat_range_for_archetype(deck_size: int, archetype: str) -> str:
        """Get threat range for specific archetype."""
        if deck_size == 100:
            return "25-30"
        else:
            return "20-24"

    @staticmethod
    def _get_control_spell_distribution(spell_count: int) -> str:
        """Get control spell distribution."""
        removal_count = int(spell_count * 0.5)
        finishers = int(spell_count * 0.15)
        return f"{removal_count}+ answers, {finishers}+ finishers"

    @staticmethod
    def _get_combo_spell_distribution(spell_count: int) -> str:
        """Get combo spell distribution."""
        combo_pieces = int(spell_count * 0.25)
        tutors = int(spell_count * 0.15)
        protection = int(spell_count * 0.15)
        draw = int(spell_count * 0.20)
        return f"Combo pieces ({combo_pieces}+), tutors ({tutors}+), protection ({protection}+), card draw ({draw}+)"

    @staticmethod
    def build_intent_parser_prompt(format_name: str = "Standard") -> str:
        """
        Generate format-aware system prompt for intent parsing.

        Args:
            format_name: Format to parse intent for

        Returns:
            System prompt string for intent parser
        """
        rules = FormatRules.get_rules(format_name)
        is_singleton = rules["singleton_rule"]
        copy_limit = rules["copy_limit"]

        prompt = f"""You are an expert at parsing user intents for Magic: The Gathering deck modifications.

Your goal is to understand what the user wants to change about their deck and
extract structured, actionable modifications.

FORMAT CONTEXT: {format_name}
{"- SINGLETON FORMAT: Only 1 copy of non-basic-land cards allowed" if is_singleton else f"- Standard format: Max {copy_limit} copies per card"}

INTENT TYPES:
1. **ADD**: User wants to add new cards to the deck
   - Examples: "Add more removal", "Add 4x Lightning Bolt", "Include counterspells"
   - Extract: Card names (if specific) or card types/categories (if abstract)

2. **REMOVE**: User wants to remove existing cards
   - Examples: "Remove all 6+ CMC cards", "Cut Lightning Bolt", "Take out slow cards"
   - Extract: Card names or conditions for removal

3. **REPLACE**: User wants to swap specific cards
   - Examples: "Replace Lightning Bolt with Shock", "Swap expensive cards for budget options"
   - Extract: Old card name and new card name

4. **OPTIMIZE**: User wants to improve deck quality
   - Examples: "Fix mana curve", "Improve consistency", "Better card draw"
   - Extract: What aspect to optimize (curve, consistency, etc.)

5. **STRATEGY_SHIFT**: User wants to change deck strategy
   - Examples: "Make deck more aggressive", "Shift to midrange", "Focus on combo"
   - Extract: Target strategy or direction

CONFIDENCE SCORING:
- 0.9-1.0: Very specific request with clear card names
- 0.7-0.9: Clear intent with abstract card types
- 0.5-0.7: Ambiguous but interpretable
- 0.3-0.5: Vague or unclear intent

OUTPUT REQUIREMENTS:
- Choose the most appropriate intent_type
- Provide clear description of what user wants
- Extract specific card_changes when possible
- List any constraints mentioned (budget, keep certain cards, etc.)
- Assign appropriate confidence score

IMPORTANT:
- Be conservative with quantities for singleton formats (max 1 copy)
- For non-singleton formats, default to 4 copies for consistency unless specified
- Extract ALL card changes mentioned, not just the first one
- If intent is unclear, use OPTIMIZE with low confidence
"""

        return prompt
