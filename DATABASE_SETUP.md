# SQLite Database Setup

The system now uses SQLite as a fallback for cache misses, providing access to all MTG cards without needing to preload everything into memory.

## Architecture

```
User Query → Extract Card Name
    ↓
Check L1 Cache → Found? Return (0.001ms)
    ↓ MISS
Check L2 Cache → Found? Return (0.001ms)
    ↓ MISS
Check L3 Cache → Found? Return (0.001ms)
    ↓ MISS
Query SQLite DB → Found? Cache to L3 & Return (0.5-5ms)
    ↓ NOT FOUND
LLM uses training data
```

## Setup Instructions

### Option 1: Build Database from MTGJSON (Recommended)

1. **Download MTGJSON AllPrintings.json:**
   ```bash
   # Visit https://mtgjson.com/downloads/all-files/
   # Download AllPrintings.json (~1GB)
   # Place it in: data/mtgjson/AllPrintings.json
   ```

2. **Build the database:**
   ```bash
   python -m mtg_cag_system.scripts.build_database
   ```

   This will:
   - Parse AllPrintings.json
   - Create `data/cards.db` SQLite database
   - Insert ~100,000+ cards
   - Create indexes for fast lookups
   - Take 2-5 minutes

3. **Start the server:**
   ```bash
   python -m mtg_cag_system.main
   ```

### Option 2: Run Without Database (Limited Mode)

If you don't build the database, the system will still work but only with:
- Sample cards preloaded at startup (Lightning Bolt, etc.)
- LLM's training data for other cards

No database error will occur - it gracefully degrades.

## Database Schema

```sql
CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mana_cost TEXT,
    cmc REAL DEFAULT 0,
    colors TEXT,           -- JSON array
    color_identity TEXT,   -- JSON array
    type_line TEXT,
    types TEXT,            -- JSON array
    subtypes TEXT,         -- JSON array
    oracle_text TEXT,
    power TEXT,
    toughness TEXT,
    loyalty TEXT,
    set_code TEXT,
    rarity TEXT,
    legalities TEXT,       -- JSON object
    keywords TEXT          -- JSON array
);

-- Indexes
CREATE INDEX idx_name ON cards(name COLLATE NOCASE);
CREATE INDEX idx_set ON cards(set_code);
CREATE INDEX idx_cmc ON cards(cmc);
CREATE INDEX idx_rarity ON cards(rarity);

-- Full-text search
CREATE VIRTUAL TABLE cards_fts USING fts5(
    name, oracle_text, type_line,
    content=cards
);
```

## Performance

| Metric | Value |
|--------|-------|
| **Database size** | ~200-500MB |
| **Card count** | ~100,000+ |
| **Startup time** | ~0.01s (with existing DB) |
| **Build time** | 2-5 minutes (one-time) |
| **Lookup time** | 0.5-5ms (cache miss) |
| **Cached lookup** | 0.001ms (L1 hit) |

## Query Examples

The database service supports:

```python
# Exact name lookup
card = db.get_card_by_name("Lightning Bolt")

# Fuzzy search
cards = db.fuzzy_search("light")  # Finds "Lightning Bolt"

# Complex filtering
cards = db.search_cards(
    query="draw",           # Full-text search
    colors=["U"],          # Blue cards only
    cmc_max=3,             # CMC ≤ 3
    types=["Instant"],     # Instants only
    limit=20
)
```

## Cache Behavior

1. **First query for "Lightning Bolt":**
   - L1/L2/L3 miss → Query SQLite (5ms)
   - Store in L3 cache
   - Return card

2. **Second query for "Lightning Bolt":**
   - L3 hit → Return from cache (0.001ms)
   - 1000x faster!

3. **Popular cards:**
   - After 5+ accesses, promoted from L3 → L2 → L1
   - L1 hits are instant

## Troubleshooting

### Database not found
```
⚠️  Database not found at ./data/cards.db
   Run 'python -m mtg_cag_system.scripts.build_database' to create it
```
**Solution:** Follow setup instructions above

### JSON file not found
```
❌ Error: MTGJSON file not found at ./data/mtgjson/AllPrintings.json
```
**Solution:** Download from https://mtgjson.com/downloads/all-files/

### Build takes too long
- Normal: 2-5 minutes on modern systems
- If >10 minutes: Check disk speed, RAM available
- Progress updates every 1000 cards

## Files Created

```
data/
├── cards.db              # SQLite database (200-500MB)
└── mtgjson/
    └── AllPrintings.json # Source data (1GB, gitignored)
```

## Distribution

When deploying your app:
1. Build `cards.db` once
2. Ship the `.db` file with your app
3. Users don't need to rebuild it!

The database is self-contained and portable.
