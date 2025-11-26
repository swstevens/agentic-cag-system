# DeckAnalyzerAgent - LLM-Based Deck Analysis

## Overview

The `DeckAnalyzerAgent` is a sophisticated LLM-powered agent that provides comprehensive Magic: The Gathering deck analysis. It replaces rule-based decision trees with context-aware, intelligent analysis using structured Pydantic outputs.

## Architecture

### Components

1. **DeckAnalyzerAgent** (`mtg_cag_system/agents/deck_analyzer_agent.py`)
   - Main agent class inheriting from `BaseAgent`
   - Uses Pydantic AI for structured LLM outputs
   - Provides comprehensive deck analysis with detailed reasoning

2. **Pydantic Models** (`mtg_cag_system/models/deck_analysis.py`)
   - `DeckAnalysisResult`: Top-level analysis result
   - `ManaCurveAnalysis`: Mana curve evaluation
   - `LandRatioAnalysis`: Land ratio assessment
   - `SynergyDetection`: Card synergy detection
   - `WinConditionAnalysis`: Win condition evaluation
   - `ArchetypeConsistency`: Archetype adherence scoring
   - `DeckStrengths` & `DeckWeaknesses`: Strengths/weaknesses
   - Quality enums: `CurveQuality`, `LandRatioQuality`

## Key Features

### 1. Archetype-Specific Analysis

The system understands and evaluates decks based on their declared archetype:

- **Aggro**: Fast, low-curve decks (avg CMC 1.5-2.5, 30-40% lands)
- **Midrange**: Value-oriented decks (avg CMC 2.5-3.5, 38-45% lands)
- **Control**: Reactive decks (avg CMC 2.5-4.0, 40-48% lands)
- **Combo**: Combination decks (avg CMC 2.0-3.5, 35-42% lands)

### 2. Comprehensive System Prompt

The agent includes an extensive system prompt with:
- Detailed archetype expectations and thresholds (from original decision trees)
- Example analyses of both good and poor decks
- Quality assessment frameworks
- Specific evaluation criteria

### 3. Structured Output

All analysis results are strongly-typed Pydantic models, ensuring:
- Consistent data structure
- Type safety
- Easy serialization/deserialization
- Clear API contracts

### 4. Context-Aware Recommendations

Unlike rule-based systems, the LLM can:
- Identify nuanced synergies and combos
- Provide context-specific recommendations
- Understand complex card interactions
- Recognize strategic patterns

## Usage

### Basic Example

```python
from mtg_cag_system.agents.deck_analyzer_agent import DeckAnalyzerAgent

# Initialize agent
analyzer = DeckAnalyzerAgent(model_name="openai:gpt-4")

# Analyze a deck
result = await analyzer.analyze_full_deck(
    cards=deck_cards,
    archetype="aggro",
    deck_format="Modern",
    deck_size=60
)

print(f"Overall Score: {result['overall_score']}/100")
print(f"Competitive: {result['is_competitive']}")
```

### Integration with DeckBuilderService

```python
from mtg_cag_system.services.deck_builder_service import DeckBuilderService
from mtg_cag_system.agents.deck_analyzer_agent import DeckAnalyzerAgent

# Initialize with analyzer agent
analyzer = DeckAnalyzerAgent()
deck_builder = DeckBuilderService(
    knowledge_agent=knowledge_agent,
    symbolic_agent=symbolic_agent,
    card_lookup=card_lookup,
    analyzer_agent=analyzer  # Optional - falls back to legacy if None
)

# The service will automatically use LLM-based analysis
deck_result = await deck_builder.build_deck(requirements)
```

## Output Structure

The `DeckAnalysisResult` includes:

```python
{
    "overall_score": 85.0,  # 0-100
    "overall_assessment": "Strong aggro deck with excellent synergies...",

    "mana_curve": {
        "average_cmc": 1.8,
        "curve_quality": "excellent",
        "curve_distribution": {"0": 0, "1": 16, "2": 8, ...},
        "focus_percentage": 80.0,
        "recommendations": [...]
    },

    "land_ratio": {
        "land_count": 20,
        "land_percentage": 33.3,
        "ratio_quality": "good",
        "recommended_land_count": 20,
        "recommendations": [...]
    },

    "synergies": [
        {
            "name": "Prowess + High Spell Density",
            "card_names": ["Monastery Swiftspear", "Lightning Bolt", ...],
            "description": "Prowess creatures benefit from...",
            "strength": "strong"
        }
    ],

    "win_conditions": {
        "primary_win_conditions": ["Aggressive creature beatdown with burn finish"],
        "backup_win_conditions": [],
        "win_condition_quality": "excellent",
        "recommendations": [...]
    },

    "archetype_consistency": {
        "declared_archetype": "aggro",
        "consistency_score": 0.95,
        "archetype_strengths": ["Low mana curve", "High threat density"],
        "archetype_weaknesses": ["Limited card advantage"],
        "recommendations": [...]
    },

    "strengths": {
        "strong_matchups": ["Slower midrange decks", "Combo decks"],
        "key_cards": ["Lightning Bolt", "Monastery Swiftspear"],
        "unique_advantages": ["Fast clock", "Consistent draws"]
    },

    "weaknesses": {
        "weak_matchups": ["Lifegain decks", "Heavy removal"],
        "vulnerabilities": ["Board wipes", "Life gain"],
        "missing_elements": ["Card advantage engines"]
    },

    "priority_improvements": [
        "Consider adding sideboard hate for lifegain",
        "Include more reach to close out games"
    ],

    "is_competitive": true,
    "needs_major_changes": false
}
```

## Advantages Over Legacy DeckAnalyzer

### Legacy (Rule-Based)
- ❌ Hardcoded archetype thresholds
- ❌ Manual combo pattern definitions
- ❌ Simple numeric scoring
- ❌ Limited to predefined synergies
- ❌ No contextual understanding
- ✅ Fast and deterministic
- ✅ No API costs

### New (LLM-Based)
- ✅ Context-aware analysis
- ✅ Discovers novel synergies
- ✅ Nuanced recommendations
- ✅ Understands card interactions
- ✅ Structured, comprehensive output
- ✅ Learns from system prompt examples
- ❌ Requires API calls (cost)
- ❌ Non-deterministic
- ❌ Slower than rule-based

## Configuration

### Model Selection

The agent supports any OpenAI-compatible model:

```python
# Default: GPT-4
analyzer = DeckAnalyzerAgent(model_name="openai:gpt-4")

# Or use GPT-3.5 for faster/cheaper analysis
analyzer = DeckAnalyzerAgent(model_name="openai:gpt-3.5-turbo")
```

### API Key Management

```python
# Option 1: Environment variable (recommended)
os.environ['OPENAI_API_KEY'] = 'sk-...'

# Option 2: Pass directly
analyzer = DeckAnalyzerAgent(api_key='sk-...')
```

## Testing

Run tests with:

```bash
# All deck analyzer tests
pytest tests/test_deck_analyzer_agent.py

# Specific test
pytest tests/test_deck_analyzer_agent.py::test_analyze_good_aggro_deck

# Skip tests requiring API key
pytest tests/test_deck_analyzer_agent.py -k "not skipif"
```

Note: Tests requiring OpenAI API access are automatically skipped if `OPENAI_API_KEY` is not set.

## Examples

See `examples/deck_analyzer_example.py` for a complete working example.

## Future Enhancements

Potential improvements:
1. **Few-Shot Learning**: Include real tournament-winning decklists in prompt
2. **Meta Awareness**: Consider current format meta-game
3. **Matchup Analysis**: Predict performance against specific deck types
4. **Sideboard Suggestions**: Recommend sideboard cards
5. **Budget Optimization**: Suggest budget-friendly alternatives
6. **Multi-Format Support**: Tailor analysis to specific format nuances
7. **Historical Comparison**: Compare against successful similar decks

## Migration Guide

### For Existing Code Using DeckAnalyzer

```python
# Old approach
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer
analysis = DeckAnalyzer.analyze_full_deck(cards, archetype)

# New approach (async)
from mtg_cag_system.agents.deck_analyzer_agent import DeckAnalyzerAgent
analyzer = DeckAnalyzerAgent()
analysis = await analyzer.analyze_full_deck(cards, archetype)
```

Both approaches return similar dictionary structures, but the new agent provides richer, more detailed analysis.

## Contributing

When improving the DeckAnalyzerAgent:
1. Update the system prompt with better examples
2. Refine archetype thresholds based on meta data
3. Add new synergy detection patterns
4. Improve the quality assessment criteria
5. Update tests to validate new features

## License

Same as parent project.
