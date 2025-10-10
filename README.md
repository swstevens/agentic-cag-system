# MTG CAG System

A Magic: The Gathering deck building assistant using Cache-Augmented Generation (CAG) and multi-agent architecture.

## Architecture

### Agents
- **Scheduling Agent**: Plans multi-step workflows and coordinates other agents
- **Knowledge Fetch Agent**: Retrieves card data from preloaded CAG context
- **Symbolic Reasoning Agent**: Validates deck legality and constraints

### Multi-Tier Cache
- **L1 (Hot)**: Frequently accessed cards (200 entries)
- **L2 (Warm)**: Patterns and relationships (1000 entries)
- **L3 (Cold)**: Historical data (10000 entries)

## Setup

1. Create and activate a virtual environment:
```bash
# Create virtual environment
python3 -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **(Recommended) Set up SQLite database with all MTG cards:**
```bash
# Download AllPrintings.json from https://mtgjson.com/
# Place it in: data/mtgjson/AllPrintings.json

# Build database (takes 2-5 minutes, one-time setup)
python -m mtg_cag_system.scripts.build_database
```

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed instructions.

5. Run the server:
```bash
python -m mtg_cag_system.main
```

## API Endpoints

### Query Processing
- `POST /api/v1/query` - Process a deck building query
- `GET /api/v1/cards/{card_name}` - Get specific card details
- `GET /api/v1/cards` - Search for cards
- `POST /api/v1/deck/validate` - Validate deck legality

### System Management
- `GET /api/v1/cache/stats` - Get cache statistics
- `POST /api/v1/cache/clear/{tier}` - Clear cache tier
- `GET /api/v1/agents/status` - Get agent status
- `GET /health` - Health check

## Example Usage

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/query",
        params={
            "query_text": "Build me a red aggro deck for Standard",
            "session_id": "user_123"
        }
    )
    print(response.json())
```

## Testing

```bash
# Start the server
python -m mtg_cag_system.main

# In another terminal, test the endpoints
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/api/v1/query?query_text=What+are+the+best+blue+cards&session_id=test"
```

## Project Structure

```
mtg_cag_system/
├── models/          # Pydantic models
├── services/        # Business logic services
├── agents/          # Pydantic AI agents
├── controllers/     # Orchestration logic
├── routers/         # FastAPI route handlers
├── config.py        # Configuration management
└── main.py          # Application entry point
```

## Development

To run in development mode with auto-reload:
```bash
uvicorn mtg_cag_system.main:app --reload
```

## License

MIT
