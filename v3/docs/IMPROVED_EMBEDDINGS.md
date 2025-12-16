# Improved Card Embeddings for Semantic Search

## Overview

The card embedding generation in [vector_service.py](../services/vector_service.py) has been significantly enhanced to capture strategic deck-building context. This enables the LLM to find cards based on nuanced queries like "anti-synergy with graveyard strategies" or "aggressive threats with immediate impact".

## What Changed

### Before (Simple Embeddings)

```python
# Old approach: Just concatenate basic info
text_content = f"{card.name}. {card.type_line}. CMC {card.cmc}. {card.oracle_text}"
```

**Problems:**
- No strategic context
- Can't distinguish between "good in aggro" vs "good in control"
- No synergy/anti-synergy information
- Miss nuanced deck-building considerations

### After (Context-Rich Embeddings)

The new approach generates rich text that includes:

1. **Basic Identity**
   - Name, type line, mana cost, colors
   - Power/toughness, loyalty
   - Keywords

2. **Strategic Context Tags** (NEW!)
   - Synergy indicators
   - Anti-synergy warnings
   - Strategic roles
   - Format considerations

## Strategic Tagging System

### Synergy Indicators

Tags that help identify cards that work well together:

```python
# Graveyard synergies
"Synergy: Graveyard strategies. Works well with self-mill, sacrifice effects, and reanimation"

# Tribal synergies
"Synergy: Goblin tribal. Benefits from or enables Goblin tribal strategies"

# +1/+1 counters
"Synergy: +1/+1 counters. Works with proliferate, counter manipulation, and counters-matter cards"

# Artifact strategies
"Synergy: Artifact strategies. Enables metalcraft, affinity, and artifact-matters effects"

# Spellslinger
"Synergy: Spellslinger decks. Rewards casting instant and sorcery spells"

# Tokens
"Synergy: Token strategies. Creates or benefits from token generation"

# Sacrifice
"Synergy: Sacrifice strategies. Either requires sacrifices or rewards sacrificing permanents"

# Life gain
"Synergy: Life gain strategies. Triggers or benefits from life gain effects"
```

### Anti-Synergy Warnings

Tags that warn about conflicts with certain strategies:

```python
# Exile removal conflicts with graveyard
"Anti-synergy: Conflicts with graveyard strategies. Exiling prevents graveyard recursion"

# Graveyard hate
"Anti-synergy: Graveyard hate. Disrupts graveyard-based strategies - avoid in graveyard decks"

# Symmetric discard
"Anti-synergy: Symmetric discard. Conflicts with strategies that value card advantage"

# Board wipes in creature decks
"Anti-synergy: Avoid in creature-heavy decks. Punishes your own board presence"
```

### Strategic Roles

Tags that identify what function a card serves:

```python
# Aggro
"Role: Aggressive one-drop. Critical for fast starts in aggro strategies"
"Role: Aggressive threat with immediate impact. Excellent for aggro strategies"
"Role: Efficient aggressive threat. Good power-to-cost ratio for aggressive decks"
"Role: Evasive threat. Can push damage through blockers effectively"

# Control
"Role: Late-game finisher. Suitable for control decks that stall until big threats"
"Role: Board wipe. Clears multiple threats - essential for control strategies"
"Role: Counterspell. Disrupts opponent's strategy by countering spells"

# Card Advantage
"Role: Card advantage engine. Helps maintain resources in longer games"

# Removal
"Role: Creature removal. Answers opposing threats"
"Role: Flexible removal. Can target multiple permanent types"

# Ramp
"Role: Mana acceleration. Enables casting expensive spells earlier"

# Protection
"Role: Protection. Shields important permanents from removal"

# Disruption
"Role: Hand disruption. Forces opponent to discard, disrupting their gameplan"

# Combo
"Role: Combo enabler. Potential infinite or game-ending combo piece"
```

### Format Considerations

Tags about format suitability:

```python
# Commander
"Format consideration: Well-suited for Commander format with higher CMC tolerance"

# Aggressive formats
"Format consideration: Excellent for aggressive formats like Standard, Modern, and Pioneer"
```

## Example: Lightning Bolt

**Old embedding text:**
```
Lightning Bolt. Instant. CMC 1. Lightning Bolt deals 3 damage to any target.
```

**New embedding text:**
```
Lightning Bolt - Instant. Costs {R}. red card. Lightning Bolt deals 3 damage to any target.
Keywords: . Role: Efficient interaction. Low-cost spell for early game tempo.
Role: Flexible removal. Can target multiple permanent types.
Format consideration: Excellent for aggressive formats like Standard, Modern, and Pioneer.
```

## Example: Wrath of God

**Old embedding text:**
```
Wrath of God. Sorcery. CMC 4. Destroy all creatures. They can't be regenerated.
```

**New embedding text:**
```
Wrath of God - Sorcery. Costs {2}{W}{W}. white card. Destroy all creatures.
They can't be regenerated. Keywords: . Role: Board wipe. Clears multiple threats - essential for control strategies.
Anti-synergy: Avoid in creature-heavy decks. Punishes your own board presence.
```

## Example: Graveyard Card (Reanimate)

**Old embedding text:**
```
Reanimate. Sorcery. CMC 1. Put target creature card from a graveyard onto the battlefield under your control. You lose life equal to its mana value.
```

**New embedding text:**
```
Reanimate - Sorcery. Costs {B}. black card. Put target creature card from a graveyard onto
the battlefield under your control. You lose life equal to its mana value. Keywords: .
Synergy: Graveyard strategies. Works well with self-mill, sacrifice effects, and reanimation.
Role: Efficient interaction. Low-cost spell for early game tempo. Role: Combo enabler.
Potential infinite or game-ending combo piece.
```

## How This Helps the LLM

### Before: Limited Semantic Understanding

```python
# Query: "cards that synergize with graveyard strategies"
# Result: Only finds cards with "graveyard" in oracle text
# Misses: Sacrifice outlets, mill cards, death triggers
```

### After: Rich Semantic Understanding

```python
# Query: "cards that synergize with graveyard strategies"
# Result: Finds cards with synergy tag, PLUS related concepts:
#   - Self-mill effects
#   - Sacrifice outlets
#   - Death triggers
#   - Reanimation spells
#   - Cards that care about creatures dying
```

### Before: No Anti-Synergy Detection

```python
# Query: "removal for graveyard deck"
# Problem: Returns exile-based removal that conflicts with strategy
```

### After: Anti-Synergy Awareness

```python
# Query: "removal for graveyard deck"
# Result: Embedding can help LLM understand:
#   - "Exile removal" has anti-synergy tag with graveyard
#   - "Destroy effects" don't have that tag
#   - LLM can prefer destroy over exile
```

### Before: No Role Differentiation

```python
# Query: "aggressive threats"
# Problem: Returns expensive creatures, slow value engines
```

### After: Role-Based Selection

```python
# Query: "aggressive threats"
# Result: Finds cards tagged with:
#   - "Aggressive one-drop"
#   - "Efficient aggressive threat"
#   - "Evasive threat"
#   - "Aggressive threat with immediate impact"
```

## Impact on Deck Building

### Improved Queries

The LLM can now search for concepts like:

```python
# Synergy-aware queries
"cards that work with sacrifice strategies"
"tribal synergies for goblins"
"cards that benefit from artifacts"

# Anti-synergy avoidance
"removal that doesn't conflict with graveyard strategies"
"board wipes for non-creature decks"

# Role-specific queries
"aggressive one-drops for fast starts"
"evasive threats that push damage"
"late-game finishers for control"

# Strategic context
"card advantage engines for longer games"
"mana acceleration for expensive spells"
"protection for important permanents"
```

### Better Deck Coherence

The embeddings help the LLM:

1. **Build Synergistic Decks**
   - Find cards that work together
   - Identify tribal, graveyard, artifact themes
   - Build around specific mechanics

2. **Avoid Anti-Synergies**
   - Don't add graveyard hate to graveyard decks
   - Don't add board wipes to creature decks
   - Don't add symmetric effects that hurt your strategy

3. **Fill Strategic Roles**
   - Distinguish threats vs removal vs draw
   - Understand aggro vs control context
   - Match card selection to archetype

4. **Consider Format Context**
   - Know which cards fit aggressive formats
   - Understand Commander-specific needs
   - Adjust curve and role distribution

## Re-syncing Embeddings

After updating the embedding logic, re-sync the vector database:

```bash
# From project root
python v3/scripts/sync_vectors.py
```

This will regenerate all embeddings with the new strategic context.

**Note:** This operation:
- Reads all cards from SQLite
- Generates new rich embedding text for each card
- Upserts to ChromaDB (replaces old embeddings)
- May take several minutes depending on card count

## Performance Considerations

### Embedding Text Length

The new approach generates longer text per card:
- Old: ~50-100 characters
- New: ~200-500 characters (with strategic tags)

**Impact:**
- Slightly higher embedding API costs (per-token pricing)
- Richer semantic space (better search results)
- Trade-off is worth it for improved deck quality

### Tagging Performance

The `_generate_strategic_tags()` method runs on each card during sync:
- Pure Python, in-memory analysis
- No external API calls
- Negligible performance impact
- Executes in <1ms per card

### Cache Behavior

Search cache still works normally:
- Query results cached by query string
- Cache hit rate unaffected
- Re-syncing clears old embeddings but keeps cache

## Future Enhancements

Potential improvements to consider:

1. **Machine Learning Tags**
   - Train classifier to identify card roles
   - Use play data to improve synergy detection
   - Learn anti-synergies from deck win rates

2. **Meta-Aware Tags**
   - Tag cards based on tournament performance
   - Identify "staples" for each format
   - Mark "tech cards" for specific matchups

3. **Interaction Tags**
   - Identify cards that combo together
   - Mark cards that answer specific threats
   - Tag modal cards with multiple roles

4. **Quality Tiers**
   - Rate cards within their roles
   - Mark premium vs budget options
   - Identify format-specific power levels

5. **Dynamic Tagging**
   - Update tags based on new sets
   - Adjust for format rotations
   - Reflect meta shifts

## Testing Semantic Search

Test improved embeddings with semantic queries:

```python
from v3.services.vector_service import VectorService
from v3.database.card_repository import CardRepository

vector_service = VectorService()
card_repo = CardRepository(db_service, vector_service=vector_service)

# Test synergy-aware search
cards = card_repo.semantic_search(
    "cards that synergize with graveyard strategies",
    limit=10
)

# Test anti-synergy avoidance
cards = card_repo.semantic_search(
    "removal that doesn't exile for graveyard deck",
    limit=10
)

# Test role-specific search
cards = card_repo.semantic_search(
    "aggressive one-drop creatures",
    limit=10
)
```

The improved embeddings should return more contextually relevant results.
