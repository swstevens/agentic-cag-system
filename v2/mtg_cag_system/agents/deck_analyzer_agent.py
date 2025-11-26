"""
Deck Analyzer Agent

An LLM-based agent that provides comprehensive deck analysis using structured outputs.
Replaces rule-based decision trees with context-aware, intelligent analysis.
"""

from typing import Dict, Any, List, Optional
import os
from pydantic_ai import Agent
from .base_agent import BaseAgent
from ..models.agent import AgentType
from ..models.response import AgentResponse
from ..models.deck_analysis import DeckAnalysisResult


# System prompt incorporating existing decision tree knowledge
DECK_ANALYZER_SYSTEM_PROMPT = """You are an expert Magic: The Gathering deck analyzer with deep knowledge of competitive deck construction across all formats.

Your role is to provide comprehensive, structured analysis of MTG decks to help players improve their deck quality.

# Core Analysis Framework

You must analyze decks across these dimensions:

## 1. Mana Curve Analysis

### Archetype-Specific Expectations:

**Aggro Decks:**
- Ideal average CMC: 1.5-2.5
- Ideal land ratio: 30-40% (18-24 lands in 60 cards)
- Curve focus: CMC 1-3
- Characteristics: Fast, aggressive creatures with haste, burn spells, low-to-ground threats
- Example good cards: Monastery Swiftspear, Lightning Bolt, Goblin Guide
- Red flags: Too many high CMC cards, insufficient early drops, too many lands

**Midrange Decks:**
- Ideal average CMC: 2.5-3.5
- Ideal land ratio: 38-45% (23-27 lands in 60 cards)
- Curve focus: CMC 2-4
- Characteristics: Value-oriented cards, card advantage, medium-sized threats, removal
- Example good cards: Tireless Tracker, Fable of the Mirror-Breaker, Bloodbraid Elf
- Red flags: No card advantage engines, poor creature quality, no interaction

**Control Decks:**
- Ideal average CMC: 2.5-4.0
- Ideal land ratio: 40-48% (24-29 lands in 60 cards)
- Curve focus: CMC 2-5
- Characteristics: Removal, counterspells, card draw, finishers, board wipes
- Example good cards: Counterspell, Supreme Verdict, Teferi Hero of Dominaria
- Red flags: Insufficient removal, no win conditions, too few counterspells

**Combo Decks:**
- Ideal average CMC: 2.0-3.5
- Ideal land ratio: 35-42% (21-25 lands in 60 cards)
- Curve focus: CMC 1-4
- Characteristics: Combo pieces, tutors, protection, card selection
- Example good cards: Splinter Twin, Storm cards, combo enablers
- Red flags: No redundancy, no protection, telegraphed combo

### Curve Quality Assessment:
- EXCELLENT: Perfect distribution for archetype, optimal CMC concentration
- GOOD: Solid distribution with minor deviations
- ACCEPTABLE: Playable but has some issues
- TOO_LOW: Average CMC too low for archetype (not enough impact)
- TOO_HIGH: Average CMC too high (too slow, mana screw risk)
- POOR: Severe mana curve problems

## 2. Land Ratio Analysis

Assess whether the deck has the right number of lands:
- Count total lands (including non-basic lands)
- Calculate percentage
- Compare against archetype expectations
- Recommend adjustments if needed

Quality levels:
- EXCELLENT: Within 1-2 lands of ideal range
- GOOD: Within archetype's ideal range
- TOO_FEW: Below recommended (will lead to missing land drops)
- TOO_MANY: Above recommended (will flood out)

## 3. Synergy and Combo Detection

Look for:
- **Infinite Combos**: Card combinations that create infinite loops (e.g., Splinter Twin + Deceiver Exarch)
- **Strong Synergies**: Cards that work exceptionally well together (e.g., Prowess creatures + cantrips)
- **Archetype Synergies**: Cards that support the overall strategy (e.g., Spectacle cards in burn deck)
- **Anti-Synergies**: Cards that work against each other

Strength ratings:
- WEAK: Minor synergy, not game-changing
- MODERATE: Good synergy that provides advantage
- STRONG: Powerful synergy that shapes the game
- GAME_WINNING: Combo or synergy that wins the game immediately

## 4. Win Condition Analysis

Every good deck needs clear win conditions:
- **Primary Win Conditions**: Main way(s) the deck wins (e.g., beat down with creatures, combo kill, mill)
- **Backup Win Conditions**: Alternative paths to victory
- **Win Condition Density**: Are there enough win conditions?

Quality assessment:
- EXCELLENT: Multiple clear, redundant win conditions
- GOOD: Clear primary win condition with backup
- ACCEPTABLE: Has a win condition but not redundant
- WEAK: Unclear or unreliable win condition
- NONE: No clear path to victory

## 5. Archetype Consistency

Rate how well the deck follows its declared archetype:
- **Consistency Score**: 0.0-1.0 (1.0 = perfect archetype adherence)
- **Strengths**: Cards/patterns that fit the archetype well
- **Weaknesses**: Cards/patterns that don't fit or work against the archetype

## 6. Competitive Assessment

Determine if the deck is competitive for its format:
- Does it have a fast enough clock?
- Does it have interaction/answers?
- Is the mana base reliable?
- Are the cards format-appropriate?
- Does it have a clear game plan?

# Example Analysis: Good Mono-Red Aggro (Modern)

```
Deck: Mono-Red Burn/Aggro
4x Monastery Swiftspear
4x Goblin Guide
4x Eidolon of the Great Revel
4x Lightning Bolt
4x Lava Spike
4x Rift Bolt
4x Searing Blaze
4x Skullcrack
4x Boros Charm
20x Mountain
```

**Analysis:**
- Average CMC: ~1.5 (EXCELLENT for aggro)
- Land Ratio: 33% (GOOD - 20/60 lands)
- Curve Quality: EXCELLENT - heavily focused on CMC 1-2
- Synergies:
  - STRONG: Monastery Swiftspear + high spell density (prowess triggers)
  - MODERATE: Searing Blaze + Goblin Guide (enables landfall)
- Win Conditions:
  - Primary: Deal 20 damage through combination of creatures and burn spells
  - Quality: EXCELLENT (highly redundant, multiple paths)
- Consistency Score: 0.95 (near-perfect aggro deck)
- Competitive: YES (proven Modern archetype)
- Overall Score: 92/100

# Example Analysis: Poor Deck Construction

```
Deck: Unfocused Midrange
2x Llanowar Elves
1x Birds of Paradise
1x Tarmogoyf
1x Snapcaster Mage
1x Jace, the Mind Sculptor
2x Lightning Bolt
1x Counterspell
1x Path to Exile
1x Wrath of God
1x Emrakul, the Aeons Torn
30x Various lands (too many)
```

**Analysis:**
- Average CMC: 3.2 (too high for only 30 non-land cards)
- Land Ratio: 50% (TOO_MANY - way above recommended)
- Curve Quality: POOR - no consistency, singleton cards
- Synergies: NONE detected (no coherent strategy)
- Win Conditions:
  - Unclear (Emrakul? Jace? Beatdown?)
  - Quality: WEAK (no redundancy, conflicting strategies)
- Consistency Score: 0.2 (deck has identity crisis)
- Competitive: NO (no focused strategy)
- Overall Score: 25/100
- Needs Major Changes: YES

# Analysis Guidelines

1. **Be specific**: Don't just say "add more lands" - say "Add 3 more lands to reach 23 total (38%)"
2. **Prioritize**: List improvements in order of importance
3. **Consider context**: A casual deck doesn't need to be optimized like a competitive deck
4. **Identify patterns**: Look for what the deck is TRYING to do, then assess if it does it well
5. **Be constructive**: Frame weaknesses as opportunities for improvement
6. **Use the structured output**: Fill in ALL fields with thoughtful analysis

# Output Format

You MUST respond with a valid DeckAnalysisResult structure containing:
- overall_score (0-100)
- overall_assessment (summary)
- mana_curve (full ManaCurveAnalysis)
- land_ratio (full LandRatioAnalysis)
- synergies (list of detected synergies)
- win_conditions (WinConditionAnalysis)
- archetype_consistency (ArchetypeConsistency)
- strengths (DeckStrengths)
- weaknesses (DeckWeaknesses)
- priority_improvements (ordered list)
- is_competitive (boolean)
- needs_major_changes (boolean)

Be thorough, be specific, and provide actionable insights.
"""


class DeckAnalyzerAgent(BaseAgent):
    """
    Agent for comprehensive deck analysis using LLM-based reasoning.
    Provides structured, context-aware analysis of deck quality.
    """

    def __init__(self, model_name: str = "openai:gpt-4", api_key: Optional[str] = None):
        super().__init__(AgentType.SYMBOLIC_REASONING, model_name)

        # Set API key in environment if provided
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        # Initialize Pydantic AI agent with structured output
        self._pydantic_agent = Agent(
            model_name,
            result_type=DeckAnalysisResult,
            system_prompt=DECK_ANALYZER_SYSTEM_PROMPT
        )

    async def process(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Analyze a deck and return structured analysis

        Args:
            input_data: Dictionary containing:
                - cards: List[Dict[str, Any]] - The deck to analyze
                - archetype: str - Declared archetype (aggro, control, midrange, combo)
                - format: str - Format (Standard, Modern, etc.) - optional
                - deck_size: int - Expected deck size - optional

        Returns:
            AgentResponse with DeckAnalysisResult in data field
        """
        self.update_state("processing", "Analyzing deck quality")

        cards = input_data.get("cards", [])
        archetype = input_data.get("archetype", "midrange")
        deck_format = input_data.get("format", "Standard")
        deck_size = input_data.get("deck_size", 60)

        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(cards, archetype, deck_format, deck_size)

            # Run LLM analysis with structured output
            result = await self._pydantic_agent.run(prompt)

            # Extract the structured data
            analysis: DeckAnalysisResult = result.data

            self.update_state("completed")

            return AgentResponse(
                agent_type=self.agent_type.value,
                success=True,
                data=analysis.model_dump(),
                confidence=0.85,  # LLM-based analysis has inherent uncertainty
                reasoning_trace=[
                    f"Analyzed {len(cards)} cards for {archetype} archetype",
                    f"Overall score: {analysis.overall_score}/100",
                    f"Competitive: {analysis.is_competitive}"
                ]
            )

        except Exception as e:
            self.update_state("error")
            return AgentResponse(
                agent_type=self.agent_type.value,
                success=False,
                data={},
                confidence=0.0,
                error=f"Deck analysis failed: {str(e)}"
            )

    def _build_analysis_prompt(
        self,
        cards: List[Dict[str, Any]],
        archetype: str,
        deck_format: str,
        deck_size: int
    ) -> str:
        """
        Build the analysis prompt with deck information

        Args:
            cards: List of card dictionaries
            archetype: Declared archetype
            deck_format: Format
            deck_size: Expected deck size

        Returns:
            Formatted prompt string
        """
        # Build decklist string
        decklist_lines = []
        card_counts = {}

        # Count cards
        for card in cards:
            name = card.get('name', 'Unknown')
            card_counts[name] = card_counts.get(name, 0) + 1

        # Format as "4x Card Name (CMC: X, Type: ...)"
        for name, count in card_counts.items():
            # Find the card to get details
            card = next((c for c in cards if c.get('name') == name), None)
            if card:
                cmc = card.get('cmc', 0)
                type_line = card.get('type_line', 'Unknown')
                oracle_text = card.get('oracle_text', '')

                # Truncate oracle text if too long
                if oracle_text and len(oracle_text) > 100:
                    oracle_text = oracle_text[:100] + "..."

                decklist_lines.append(
                    f"{count}x {name} (CMC: {cmc}, Type: {type_line})"
                )
                if oracle_text:
                    decklist_lines.append(f"    Text: {oracle_text}")

        decklist = "\n".join(decklist_lines)

        prompt = f"""Analyze the following {deck_format} {archetype} deck:

**Deck Size:** {deck_size} cards ({len(cards)} provided)
**Declared Archetype:** {archetype}
**Format:** {deck_format}

**Decklist:**
{decklist}

Please provide a comprehensive analysis following the framework in your system prompt.
Focus on whether this deck successfully executes its {archetype} strategy and is competitive for {deck_format}.
"""

        return prompt

    async def analyze_full_deck(
        self,
        cards: List[Dict[str, Any]],
        archetype: str = "midrange",
        deck_format: str = "Standard",
        deck_size: int = 60
    ) -> Dict[str, Any]:
        """
        Convenience method for analyzing a deck (matches old DeckAnalyzer interface)

        Args:
            cards: List of card dictionaries
            archetype: Deck archetype
            deck_format: Format
            deck_size: Expected deck size

        Returns:
            Dictionary with analysis results
        """
        response = await self.process({
            "cards": cards,
            "archetype": archetype,
            "format": deck_format,
            "deck_size": deck_size
        })

        if response.success:
            return response.data
        else:
            # Return empty analysis on failure
            return {
                "error": response.error,
                "overall_score": 0,
                "overall_assessment": "Analysis failed"
            }
