# Vector Search for Card Similarity

## Overview

This system uses **ChromaDB** and **sentence transformers** to enable semantic similarity search for MTG cards. Instead of just filtering by colors/types, the deck builder can now find cards that:

- Have similar mechanics (e.g., "create tokens", "draw cards")
- Work well together (synergies)
- Match a specific strategy (e.g., "aggro creatures", "removal spells")

## How It Works

### 1. One-Time Embedding Generation

**Run once when setting up:**

```bash
python scripts/build_embeddings.py
```

This script:
- Loads all ~107K cards from the database
- Creates a rich text representation of each card (name, type, oracle text, keywords, etc.)
- Generates vector embeddings using a sentence transformer model
- Saves embeddings to disk at `./data/chroma/`
- Takes ~10-30 minutes depending on hardware

### 2. Persistent Storage

Embeddings are saved to disk and automatically loaded on subsequent runs:

```python
vector_store = VectorStoreService()  # Loads from ./data/chroma/
# No need to rebuild!
```

### 3. Similarity Search

Find cards similar to a specific card:

```python
similar = vector_store.find_similar_cards(
    card_name="Llanowar Elves",
    n_results=10,
    filters={"standard_legal": True}  # Optional: only Standard-legal cards
)

# Results:
# [
#   {"name": "Elvish Mystic", "distance": 0.05, ...},
#   {"name": "Birds of Paradise", "distance": 0.12, ...},
#   {"name": "Fyndhorn Elves", "distance": 0.15, ...}
# ]
```

Find cards matching a concept:

```python
cards = vector_store.find_cards_by_concept(
    concept="cards that create token creatures",
    n_results=20,
    filters={"colors": "G"}  # Optional: only green cards
)
```

## Card Representation Strategy

Each card is converted to searchable text combining:

```
Name: Llanowar Elves
Type: Creature — Elf Druid
Cost: {G}
Colors: Green
Keywords: None
Text: {T}: Add {G}.
Stats: 1/1
Subtypes: Elf, Druid
```

This captures:
- **Mechanics** - What the card does (oracle text)
- **Tribal** - Creature types for tribal synergies
- **Stats** - P/T, CMC for curve considerations
- **Keywords** - Flying, Trample, etc. for mechanical similarities

## Metadata Filtering

ChromaDB stores metadata for each card, enabling combined vector + traditional search:

```python
# Find removal spells that are Standard-legal AND cost ≤2 mana
similar = vector_store.find_cards_by_concept(
    concept="destroy target creature",
    filters={
        "standard_legal": True,
        "cmc": {"$lte": 2}
    }
)
```

Available filters:
- `standard_legal`, `modern_legal`, `commander_legal` (bool)
- `cmc` (float)
- `colors`, `color_identity` (string, comma-separated)
- `types`, `subtypes` (string, comma-separated)
- `rarity` (string)

## Integration with Deck Builder

The deck builder can now use vector search for better card selection:

### Before (Traditional Filtering):
```python
# Get 1000 random green cards
cards = db.search_cards(colors=["G"], limit=1000)
# → Returns random mix, many don't synergize
```

### After (Vector-Enhanced):
```python
# Start with a few "seed cards" that match the strategy
seed_cards = ["Llanowar Elves", "Ghalta, Primal Hunger"]

all_cards = []
for seed in seed_cards:
    # Find cards similar to each seed
    similar = vector_store.find_similar_cards(
        card_name=seed,
        n_results=50,
        filters={"standard_legal": True, "colors": "G"}
    )
    all_cards.extend(similar)

# Also search by concept
concept_cards = vector_store.find_cards_by_concept(
    concept="aggressive green creatures with low mana cost",
    n_results=100,
    filters={"standard_legal": True}
)
all_cards.extend(concept_cards)

# Result: Better card selection with natural synergies!
```

## Performance

- **First run**: ~10-15 minutes to build embeddings for 107K cards (one-time)
- **Subsequent runs**: Instant (loads from disk)
- **Query time**: ~10-50ms for similarity search
- **Disk space**: ~500MB for 107K cards (embeddings + metadata)
- **Processing rate**: ~400 cards/second during embedding generation

## Embedding Model

Uses `all-MiniLM-L6-v2`:
- **Size**: 80MB model
- **Speed**: Fast (384-dimensional embeddings)
- **Quality**: Good for semantic similarity
- **Offline**: Works without internet after first download

Can be changed to larger models for better quality:
- `all-mpnet-base-v2` (768-dim, higher quality, slower)
- `paraphrase-multilingual` (for non-English support)

## Future Enhancements

1. **Synergy Detection**: Train on known card combos
2. **Meta-Learning**: Learn from successful decks
3. **Price Filtering**: Combine with Scryfall pricing data
4. **Deck Archetypes**: Cluster cards into deck archetypes
5. **Supabase Migration**: Move to cloud for web deployment

## Example Use Cases

### Use Case 1: Build Around a Card

```python
# "I want to build a deck around Doubling Season"
similar = vector_store.find_similar_cards(
    "Doubling Season",
    n_results=60,
    filters={"commander_legal": True}
)
# Returns cards that create tokens, use +1/+1 counters, etc.
```

### Use Case 2: Fill a Slot

```python
# "I need more 2-drop creatures for my aggro deck"
cards = vector_store.find_cards_by_concept(
    "aggressive creature with low mana cost",
    n_results=20,
    filters={"standard_legal": True, "cmc": 2}
)
```

### Use Case 3: Find Alternatives

```python
# "Lightning Bolt is too expensive, find budget alternatives"
similar = vector_store.find_similar_cards(
    "Lightning Bolt",
    n_results=10,
    filters={"modern_legal": True}
)
# Then filter by price (if integrated with Scryfall)
```

## Technical Details

### Architecture

```
┌─────────────────────────────────────────────────┐
│ MTG Cards Database (SQLite)                     │
│ - 107,196 cards                                 │
│ - Card text, types, mechanics                  │
└────────────────┬────────────────────────────────┘
                 │
                 │ One-time build
                 ↓
┌─────────────────────────────────────────────────┐
│ Vector Store (ChromaDB)                         │
│ - Persistent disk storage                      │
│ - 384-dim embeddings per card                  │
│ - Metadata for filtering                       │
└────────────────┬────────────────────────────────┘
                 │
                 │ Fast queries (10-50ms)
                 ↓
┌─────────────────────────────────────────────────┐
│ Deck Builder Service                            │
│ - Find similar cards                           │
│ - Concept-based search                         │
│ - Combined with traditional filters            │
└─────────────────────────────────────────────────┘
```

### Files

- `mtg_cag_system/services/vector_store_service.py` - Main service
- `scripts/build_embeddings.py` - One-time embedding builder
- `data/chroma/` - Persistent storage directory (not in git)

### Dependencies

```
chromadb>=0.4.0
sentence-transformers>=2.2.0
```
