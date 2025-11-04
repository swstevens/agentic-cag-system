# Deck Analyzer Migration Guide

## ⚠️ DeckAnalyzer → LLMDeckAnalyzer

The legacy `DeckAnalyzer` (rule-based) has been deprecated in favor of `LLMDeckAnalyzer` (wraps `DeckAnalyzerAgent`).

## Why Migrate?

- **Better Analysis**: LLM-based analysis provides context-aware insights instead of rigid heuristics
- **Structured Output**: Uses Pydantic models (`DeckAnalysisResult`) with comprehensive breakdowns
- **Consistent Interface**: Implements `IAnalyzer` interface for Strategy Pattern
- **Future-Proof**: DeckAnalyzer will be removed in future versions

## Migration Path

### Before (Legacy DeckAnalyzer)

```python
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer

# Static method calls (rule-based)
analysis = DeckAnalyzer.analyze_full_deck(cards, archetype="aggro")
validation = DeckAnalyzer.validate_candidate_cards(candidates, deck, format="Modern")

# Access archetype data
land_ratio = DeckAnalyzer.ARCHETYPE_CURVES['aggro']['land_ratio']
```

### After (LLMDeckAnalyzer)

```python
from mtg_cag_system.analyzers import LLMDeckAnalyzer
from mtg_cag_system.interfaces.analyzer import AnalysisContext

# Create analyzer instance
analyzer = LLMDeckAnalyzer(model_name="openai:gpt-4")

# Analyze deck (async)
context = AnalysisContext(
    archetype="aggro",
    format="Modern",
    target_deck_size=60
)

analysis_result = await analyzer.analyze(cards, context)

# Access structured results
print(f"Overall Score: {analysis_result.overall_score}")
print(f"Mana Curve Quality: {analysis_result.mana_curve.curve_quality}")
print(f"Land Ratio: {analysis_result.land_ratio.land_percentage}%")
print(f"Competitive: {analysis_result.is_competitive}")
```

## Key Differences

### 1. Instance vs Static Methods

**Legacy**: Static methods on `DeckAnalyzer` class
**New**: Instance methods on `LLMDeckAnalyzer` object

### 2. Async/Await

**Legacy**: Synchronous
**New**: Async (uses Pydantic AI under the hood)

```python
# You'll need to use await
analysis = await analyzer.analyze(cards, context)
```

### 3. Typed Inputs/Outputs

**Legacy**: Dict-based inputs and outputs
**New**: Pydantic models for type safety

```python
# Input: AnalysisContext (Pydantic model)
context = AnalysisContext(archetype="aggro", format="Modern")

# Output: DeckAnalysisResult (Pydantic model with nested structures)
result: DeckAnalysisResult = await analyzer.analyze(cards, context)
```

### 4. Richer Analysis

**New analyzer provides**:
- Overall assessment (score 0-100)
- Mana curve analysis with recommendations
- Land ratio quality assessment
- Detected synergies and combos
- Win condition analysis
- Archetype consistency scoring
- Strengths and weaknesses breakdown
- Priority improvements list

## Backward Compatibility

The legacy `DeckAnalyzer` remains available for backward compatibility but will emit deprecation warnings.

### Suppressing Warnings (Temporary)

If you need time to migrate:

```python
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    # Your legacy code here
    analysis = DeckAnalyzer.analyze_full_deck(cards, "aggro")
```

## For DeckBuilderService Users

If you're using `DeckBuilderService`, pass an analyzer instance:

```python
from mtg_cag_system.services.deck_builder_service import DeckBuilderService
from mtg_cag_system.analyzers import LLMDeckAnalyzer

# Create analyzer
analyzer = LLMDeckAnalyzer(model_name="openai:gpt-4")

# Pass to deck builder
deck_builder = DeckBuilderService(
    knowledge_agent=knowledge_agent,
    symbolic_agent=symbolic_agent,
    card_lookup_service=card_lookup_service,
    analyzer_agent=analyzer  # New: pass LLM analyzer
)
```

## Testing Migration

Update your tests to use the new analyzer:

```python
import pytest
from mtg_cag_system.analyzers import LLMDeckAnalyzer
from mtg_cag_system.interfaces.analyzer import AnalysisContext

@pytest.mark.asyncio
async def test_deck_analysis():
    analyzer = LLMDeckAnalyzer(model_name="openai:gpt-4")

    context = AnalysisContext(
        archetype="aggro",
        format="Modern",
        target_deck_size=60
    )

    result = await analyzer.analyze(test_cards, context)

    assert result.overall_score > 0
    assert result.mana_curve is not None
    assert result.land_ratio is not None
```

## Timeline

- **Now**: DeckAnalyzer deprecated, emits warnings
- **v2.0**: DeckAnalyzer removed entirely
- **Recommendation**: Migrate as soon as possible

## Questions?

See the [DeckAnalyzerAgent documentation](docs/DECK_ANALYZER_AGENT.md) for more details on the LLM-based analyzer.
