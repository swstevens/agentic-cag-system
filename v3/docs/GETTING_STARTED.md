# Getting Started with Agentic CAG System (v3)

This guide will help you set up the development environment and run the Agentic CAG System (v3).

## Prerequisites

- **OS**: Linux or macOS recommended (Windows via WSL2)
- **Python**: Version 3.10 or higher
- **Git**: For version control
- **OpenAI API Key**: Required for LLM-powered deck building

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/swstevens/agentic-cag-system.git
cd agentic-cag-system/v3
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file with your API keys and configuration:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```ini
# Required: LLM API Key
OPENAI_API_KEY=sk-your-key-here

# Optional: Alternative LLM providers
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Model selection (defaults to gpt-4o-mini)
DEFAULT_MODEL=openai:gpt-4o-mini

# Optional: Cache configuration
CACHE_SIZE=1000
```

---

## Database Setup

The system requires two databases:

1. **SQLite Database** (`v3/data/cards.db`) - Relational database for card data
2. **ChromaDB Vector Store** (`v3/data/chroma_db/`) - Vector embeddings for semantic search

### Step 1: Download MTG Card Data

Download the card database from MTGJSON:

1. Visit https://mtgjson.com/downloads/all-files/#atomiccards
2. Download **`AtomicCards.json`** (this contains all unique MTG cards)
3. Save it to a convenient location (e.g., `~/Downloads/AtomicCards.json`)

**File size note**: The `AtomicCards.json` file is approximately 100-200 MB.

### Step 2: Import Cards to SQLite Database

Run the import script to create the relational database:

```bash
# From the v3 directory
python scripts/import_cards.py ~/Downloads/AtomicCards.json
```

**What this does:**
- Creates `v3/data/cards.db` SQLite database
- Imports all cards from the JSON file
- Sets up the database schema automatically
- Takes approximately 2-5 minutes depending on your system

**Expected output:**
```
Loading cards from /home/user/Downloads/AtomicCards.json...
Found 25000+ cards to import
Importing 25000+ cards...
Successfully imported 25000+ cards
```

**Alternative: Sample Data (for testing)**

If you don't want to download the full database, you can create a small sample dataset:

```bash
python scripts/import_cards.py --sample
```

This creates about 50 sample cards for testing purposes.

### Step 3: Generate Vector Embeddings

Run the sync script to create semantic search embeddings:

```bash
# From the v3 directory
python scripts/sync_vectors.py
```

**What this does:**
- Reads all cards from `v3/data/cards.db`
- Generates rich text embeddings for each card (includes strategic context)
- Stores vectors in `v3/data/chroma_db/` ChromaDB collection
- Takes approximately 10-30 minutes for full database (uses OpenAI embeddings API)

**Expected output:**
```
INFO - Initializing services...
INFO - Using database at: /path/to/v3/data/cards.db
INFO - Using chroma at: /path/to/v3/data/chroma_db
INFO - Fetching cards from SQLite...
INFO - Found 25000+ cards.
INFO - Generating embeddings and syncing to ChromaDB...
INFO - This may take a while depending on the number of cards...
INFO - Successfully synced 25000+ cards to vector store.
INFO - Total cards in vector store: 25000+
```

**Note**: This step uses the OpenAI Embeddings API and will incur costs (approximately $1-3 for the full database). The embeddings are cached, so you only need to run this once.

### Step 4: Verify Database Setup

Check that everything is set up correctly:

```bash
python scripts/check_db.py
```

**Expected output:**
```
Database: v3/data/cards.db
Total cards: 25000+
Vector store count: 25000+

Sample cards:
  - Lightning Bolt (Instant)
  - Black Lotus (Artifact)
  - Counterspell (Instant)
  ...

✓ Database setup complete!
```

---

## Running the Application

The system consists of two main components:

### 1. Start the Backend (FastAPI)

The backend handles API requests, FSM logic, and database interactions.

```bash
# Terminal 1 (ensure venv is active and you're in v3/)
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Backend runs at:** `http://localhost:8000`

**Verify it's working:**
- Open `http://localhost:8000/docs` for interactive API documentation
- Open `http://localhost:8000/health` should return `{"status": "healthy"}`

### 2. Start the Frontend (FastHTML)

The frontend provides the chat interface and deck management UI.

```bash
# Terminal 2 (ensure venv is active and you're in v3/)
python frontend/app.py
```

**Frontend runs at:** `http://localhost:5000`

---

## Usage Guide

### Creating Your First Deck

1. Open your browser and navigate to `http://localhost:5000`
2. Type a prompt in the chat interface:
   ```
   Build me a Standard Mono-Red Aggro deck
   ```
3. The system will:
   - Parse your request (format, colors, archetype)
   - Enter the "Draft-Verify-Refine" loop
   - Build an initial deck using LLM agents
   - Verify quality (mana curve, land ratio, synergies)
   - Refine the deck if quality is below threshold
   - Return the final deck with quality metrics

**Expected time**: 30-90 seconds depending on iterations

### Modifying an Existing Deck

Once a deck is loaded, you can modify it with natural language:

```
Add more removal spells
Replace Lightning Bolt with Shock
Make the deck more aggressive
Remove all cards with CMC 6 or higher
```

Modifications are **single-pass** (faster than new deck creation).

### Saving Decks

1. Click the **"Save Deck"** button
2. Enter a name and optional description
3. The deck is saved to `v3/data/decks.db`

### Viewing Saved Decks

1. Click **"My Decks"** in the navigation
2. Filter by format or archetype
3. Click any deck to load it for editing

---

## Project Structure

```
v3/
├── api.py                  # FastAPI backend entry point
├── frontend/
│   ├── app.py             # FastHTML frontend entry point
│   └── components/        # UI components
├── data/                  # Generated data directory
│   ├── cards.db          # SQLite card database
│   ├── decks.db          # SQLite deck persistence
│   └── chroma_db/        # Vector embeddings
├── database/             # Data access layer
├── fsm/                  # Finite state machine
├── services/             # Business logic services
├── models/               # Domain models
└── scripts/              # Setup and utility scripts
```

---

## Troubleshooting

### Database Issues

**Problem**: `ERROR - Database file not found`

**Solution**:
```bash
# Ensure you ran the import script
python scripts/import_cards.py ~/Downloads/AtomicCards.json
```

**Problem**: `ERROR - Vector store empty`

**Solution**:
```bash
# Re-run the sync script
python scripts/sync_vectors.py
```

### API Key Issues

**Problem**: `AuthenticationError: Incorrect API key`

**Solution**:
- Verify `.env` file exists in `v3/` directory
- Check that `OPENAI_API_KEY` is set correctly
- Make sure there are no extra spaces or quotes

### Port Conflicts

**Problem**: `Address already in use: 0.0.0.0:8000`

**Solution**:
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or change the port in api.py
uvicorn api:app --reload --port 8001
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'v3'`

**Solution**:
```bash
# Make sure you're in the v3 directory
cd /path/to/agentic-cag-system/v3

# Use PYTHONPATH if needed
export PYTHONPATH=/path/to/agentic-cag-system:$PYTHONPATH
```

### Performance Issues

**Problem**: Deck building is very slow

**Solutions**:
- Check your internet connection (LLM API calls)
- Use a faster model: `DEFAULT_MODEL=openai:gpt-4o-mini`
- Reduce `max_iterations` in deck build requests
- Verify vector database is populated (speeds up card search)

---

## Development Tips

### Running Individual Components

**Test FSM directly:**
```bash
python scripts/example_deck_build.py
```

**Test vector search:**
```bash
python scripts/verify_search.py
```

**Check database:**
```bash
python scripts/check_db.py
```

### Resetting the System

To start fresh:

```bash
# Remove databases (will be recreated on next run)
rm -rf v3/data/cards.db v3/data/decks.db v3/data/chroma_db/

# Re-import cards
python scripts/import_cards.py ~/Downloads/AtomicCards.json
python scripts/sync_vectors.py
```

### Updating Card Data

To update with the latest MTG cards:

1. Download latest `AtomicCards.json` from MTGJSON
2. Delete old database: `rm v3/data/cards.db`
3. Re-import: `python scripts/import_cards.py ~/Downloads/AtomicCards.json`
4. Re-sync vectors: `python scripts/sync_vectors.py`

---

## Next Steps

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Understand the system architecture
- **[BACKEND_API.md](BACKEND_API.md)** - Explore the API endpoints
- **[FSM_WORKFLOWS.md](FSM_WORKFLOWS.md)** - Learn about the FSM workflow
- **[IMPROVED_EMBEDDINGS.md](IMPROVED_EMBEDDINGS.md)** - Learn about semantic search

---

## Getting Help

- **Documentation**: Check the `docs/` folder for comprehensive guides
- **API Docs**: Visit `http://localhost:8000/docs` when backend is running
- **Issues**: Report bugs or ask questions on the GitHub repository

**Happy deck building!** 🎴
