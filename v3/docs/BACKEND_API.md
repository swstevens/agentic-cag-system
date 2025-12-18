# Backend API Reference

## Overview

This document provides comprehensive backend implementation details for the v3 MTG Deck Builder API. It includes FastAPI endpoint definitions, request/response models, and Python code examples.

For frontend integration examples (JavaScript/fetch), see [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md).

## Base Configuration

### FastAPI Application

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="MTG Deck Builder API",
    description="REST API for building Magic: The Gathering decks using FSM orchestrator",
    version="3.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Request/Response Models

### Chat Models

```python
from pydantic import BaseModel
from typing import Dict, Any, Optional

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    context: Optional[Dict[str, Any]] = None
    existing_deck: Optional[Dict[str, Any]] = None  # If provided, this is a modification request

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str
    deck: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### Deck Persistence Models

```python
from typing import List

class SaveDeckRequest(BaseModel):
    """Request model for saving a deck."""
    deck: Dict[str, Any]
    name: str
    description: Optional[str] = None
    quality_score: Optional[float] = None

class SaveDeckResponse(BaseModel):
    """Response model for saving a deck."""
    success: bool
    deck_id: Optional[str] = None
    message: str
    error: Optional[str] = None

class DeckListItem(BaseModel):
    """Model for deck list item."""
    id: str
    name: str
    description: Optional[str] = None
    format: str
    archetype: Optional[str] = None
    colors: List[str]
    total_cards: int
    quality_score: Optional[float] = None
    created_at: str
    updated_at: str

class DeckListResponse(BaseModel):
    """Response model for listing decks."""
    success: bool
    decks: List[DeckListItem]
    total: int
    error: Optional[str] = None

class UpdateDeckRequest(BaseModel):
    """Request model for updating a deck."""
    deck: Dict[str, Any]
    name: Optional[str] = None
    description: Optional[str] = None
    quality_score: Optional[float] = None

class UpdateDeckResponse(BaseModel):
    """Response model for updating a deck."""
    success: bool
    message: str
    error: Optional[str] = None

class DeleteDeckResponse(BaseModel):
    """Response model for deleting a deck."""
    success: bool
    message: str
    error: Optional[str] = None
```

---

## API Endpoints

### 1. Chat Endpoint (Deck Creation & Modification)

**Endpoint:** `POST /api/chat`

**Purpose:** Unified endpoint for both new deck creation and deck modification.

**Implementation:**

```python
from v3.fsm.orchestrator import FSMOrchestrator
from v3.models.deck import Deck, DeckModificationRequest

orchestrator = FSMOrchestrator()

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process chat message and return deck building results.

    Handles both:
    - New deck creation (if no existing_deck provided)
    - Deck modification (if existing_deck provided)

    Args:
        request: Chat request with message and optional context/existing_deck

    Returns:
        Chat response with message, deck data, and any errors
    """
    try:
        # Route based on whether this is a modification or new deck
        if request.existing_deck:
            # MODIFICATION FLOW
            deck = Deck.model_validate(request.existing_deck)
            mod_request = DeckModificationRequest(
                existing_deck=deck,
                user_prompt=request.message,
                run_quality_check=False
            )
            result = await orchestrator.execute(mod_request)

            if result["success"]:
                deck_dict = result["deck"]
                modifications = result.get("modifications", {})

                response_message = f"✓ Deck modified!\\n{modifications.get('summary', '')}"
                if modifications.get('quality_after'):
                    response_message += f"\\nQuality Score: {modifications['quality_after']:.2f}"

                return ChatResponse(
                    message=response_message,
                    deck=deck_dict,
                    error=None
                )
            else:
                error_msg = result.get("error", "Modification failed")
                return ChatResponse(
                    message=f"❌ {error_msg}",
                    deck=None,
                    error=error_msg
                )

        else:
            # NEW DECK FLOW
            deck_request = parse_deck_request(request.message, request.context)
            result = await orchestrator.execute(deck_request)

            if result["success"]:
                data = result["data"]
                deck_dict = data["deck"]
                quality_metrics = data["quality_metrics"]

                # Format response message
                message_parts = [
                    f"✓ Successfully built a {deck_dict['archetype']} deck!",
                    f"\\nQuality Score: {quality_metrics['overall_score']:.2f}",
                    f"Iterations: {data['iteration_count']}",
                    f"Total Cards: {deck_dict['total_cards']}",
                ]

                if quality_metrics.get("issues"):
                    message_parts.append(f"\\nIssues: {', '.join(quality_metrics['issues'][:2])}")

                return ChatResponse(
                    message="\\n".join(message_parts),
                    deck=deck_dict,
                    error=None
                )
            else:
                error_msg = result.get("error", "Deck generation failed")
                return ChatResponse(
                    message=f"❌ {error_msg}",
                    deck=None,
                    error=error_msg
                )

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        return ChatResponse(
            message=f"❌ Error: {str(e)}",
            deck=None,
            error=str(e)
        )
```

**Request Parsing Utility:**

```python
def parse_deck_request(message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse user message to extract deck building parameters.

    Args:
        message: User's chat message
        context: Optional context from previous requests

    Returns:
        Dictionary with deck building parameters
    """
    message_lower = message.lower()

    # Extract format
    format_map = {
        "standard": "Standard",
        "modern": "Modern",
        "commander": "Commander",
        "legacy": "Legacy",
        "vintage": "Vintage",
        "pioneer": "Pioneer",
    }
    format_name = "Standard"  # default
    for key, value in format_map.items():
        if key in message_lower:
            format_name = value
            break

    # Extract colors
    color_map = {
        "white": "W",
        "blue": "U",
        "black": "B",
        "red": "R",
        "green": "G",
    }
    colors = []
    for color_name, color_code in color_map.items():
        if color_name in message_lower:
            colors.append(color_code)

    if not colors:
        colors = ["R"]  # default to red

    # Extract archetype
    archetype_map = {
        "aggro": "Aggro",
        "control": "Control",
        "midrange": "Midrange",
        "combo": "Combo",
    }
    archetype = "Aggro"  # default
    for key, value in archetype_map.items():
        if key in message_lower:
            archetype = value
            break

    return {
        "format": format_name,
        "colors": colors,
        "archetype": archetype,
        "strategy": message,
        "quality_threshold": 0.7,
        "max_iterations": 5
    }
```

---

### 2. Save Deck

**Endpoint:** `POST /api/decks`

**Implementation:**

```python
from v3.database.deck_repository import DeckRepository
from v3.database.database_service import DatabaseService

db_service = DatabaseService()
deck_repository = DeckRepository(db_service)

@app.post("/api/decks", response_model=SaveDeckResponse)
async def save_deck(request: SaveDeckRequest) -> SaveDeckResponse:
    """
    Save a deck to the database.

    Args:
        request: SaveDeckRequest with deck data and metadata

    Returns:
        SaveDeckResponse with success status and deck_id
    """
    try:
        # Validate and parse deck
        deck = Deck.model_validate(request.deck)

        # Save to database
        deck_id = deck_repository.save_deck(
            deck=deck,
            name=request.name,
            description=request.description,
            quality_score=request.quality_score
        )

        return SaveDeckResponse(
            success=True,
            deck_id=deck_id,
            message=f"Deck '{request.name}' saved successfully",
            error=None
        )

    except Exception as e:
        logger.error(f"Save deck error: {str(e)}", exc_info=True)
        return SaveDeckResponse(
            success=False,
            deck_id=None,
            message="Failed to save deck",
            error=str(e)
        )
```

---

### 3. List Decks

**Endpoint:** `GET /api/decks`

**Query Parameters:**
- `format` (optional): Filter by format (e.g., "Standard", "Commander")
- `archetype` (optional): Filter by archetype (e.g., "Aggro", "Control")
- `limit` (optional): Maximum results to return (default: 100)
- `offset` (optional): Number of results to skip for pagination (default: 0)

**Implementation:**

```python
from fastapi import Query

@app.get("/api/decks", response_model=DeckListResponse)
async def list_decks(
    format_filter: Optional[str] = Query(None, alias="format"),
    archetype_filter: Optional[str] = Query(None, alias="archetype"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> DeckListResponse:
    """
    List saved decks with optional filters.

    Args:
        format_filter: Optional format filter
        archetype_filter: Optional archetype filter
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        DeckListResponse with list of decks
    """
    try:
        decks = deck_repository.list_decks(
            format_filter=format_filter,
            archetype_filter=archetype_filter,
            limit=limit,
            offset=offset
        )

        total = deck_repository.get_deck_count(
            format_filter=format_filter,
            archetype_filter=archetype_filter
        )

        # Convert to DeckListItem models
        deck_items = [
            DeckListItem(
                id=deck["id"],
                name=deck["name"],
                description=deck.get("description"),
                format=deck["format"],
                archetype=deck.get("archetype"),
                colors=deck["colors"],
                total_cards=deck["total_cards"],
                quality_score=deck.get("quality_score"),
                created_at=deck["created_at"],
                updated_at=deck["updated_at"]
            )
            for deck in decks
        ]

        return DeckListResponse(
            success=True,
            decks=deck_items,
            total=total,
            error=None
        )

    except Exception as e:
        logger.error(f"List decks error: {str(e)}", exc_info=True)
        return DeckListResponse(
            success=False,
            decks=[],
            total=0,
            error=str(e)
        )
```

---

### 4. Get Specific Deck

**Endpoint:** `GET /api/decks/{deck_id}`

**Implementation:**

```python
from fastapi import HTTPException

@app.get("/api/decks/{deck_id}")
async def get_deck(deck_id: str):
    """
    Retrieve a specific deck by ID.

    Args:
        deck_id: UUID of the deck to retrieve

    Returns:
        Dictionary with deck data and metadata

    Raises:
        HTTPException: 404 if deck not found
    """
    try:
        deck_data = deck_repository.get_deck_by_id(deck_id)

        if not deck_data:
            raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

        return {
            "success": True,
            **deck_data,
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get deck error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 5. Update Deck

**Endpoint:** `PUT /api/decks/{deck_id}`

**Implementation:**

```python
@app.put("/api/decks/{deck_id}", response_model=UpdateDeckResponse)
async def update_deck(deck_id: str, request: UpdateDeckRequest) -> UpdateDeckResponse:
    """
    Update an existing deck.

    Args:
        deck_id: UUID of the deck to update
        request: UpdateDeckRequest with updated data

    Returns:
        UpdateDeckResponse with success status
    """
    try:
        # Validate deck data if provided
        deck = None
        if request.deck:
            deck = Deck.model_validate(request.deck)

        # Update in database
        success = deck_repository.update_deck(
            deck_id=deck_id,
            deck=deck,
            name=request.name,
            description=request.description,
            quality_score=request.quality_score
        )

        if not success:
            return UpdateDeckResponse(
                success=False,
                message=f"Deck {deck_id} not found",
                error="Deck not found"
            )

        return UpdateDeckResponse(
            success=True,
            message=f"Deck {deck_id} updated successfully",
            error=None
        )

    except Exception as e:
        logger.error(f"Update deck error: {str(e)}", exc_info=True)
        return UpdateDeckResponse(
            success=False,
            message="Failed to update deck",
            error=str(e)
        )
```

---

### 6. Delete Deck

**Endpoint:** `DELETE /api/decks/{deck_id}`

**Implementation:**

```python
@app.delete("/api/decks/{deck_id}", response_model=DeleteDeckResponse)
async def delete_deck(deck_id: str) -> DeleteDeckResponse:
    """
    Delete a deck from the database.

    Args:
        deck_id: UUID of the deck to delete

    Returns:
        DeleteDeckResponse with success status
    """
    try:
        success = deck_repository.delete_deck(deck_id)

        if not success:
            return DeleteDeckResponse(
                success=False,
                message=f"Deck {deck_id} not found",
                error="Deck not found"
            )

        return DeleteDeckResponse(
            success=True,
            message=f"Deck {deck_id} deleted successfully",
            error=None
        )

    except Exception as e:
        logger.error(f"Delete deck error: {str(e)}", exc_info=True)
        return DeleteDeckResponse(
            success=False,
            message="Failed to delete deck",
            error=str(e)
        )
```

---

### 7. Health Check

**Endpoint:** `GET /health`

**Implementation:**

```python
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
```

---

## Database Layer

### DeckRepository

The `DeckRepository` handles all database operations for deck persistence.

```python
from v3.database.deck_repository import DeckRepository
from v3.database.database_service import DatabaseService

# Initialize
db_service = DatabaseService(db_path="v3/data/decks.db")
deck_repository = DeckRepository(db_service)

# Save a deck
deck_id = deck_repository.save_deck(
    deck=deck,  # Deck model instance
    name="My Aggro Deck",
    description="Fast aggressive deck",
    quality_score=0.85
)

# List decks
decks = deck_repository.list_decks(
    format_filter="Standard",
    archetype_filter=None,
    limit=50,
    offset=0
)

# Get specific deck
deck_data = deck_repository.get_deck_by_id(deck_id)

# Update deck
success = deck_repository.update_deck(
    deck_id=deck_id,
    deck=updated_deck,
    name="Updated Name",
    quality_score=0.90
)

# Delete deck
success = deck_repository.delete_deck(deck_id)

# Get count
total = deck_repository.get_deck_count(format_filter="Commander")
```

---

## FSM Orchestrator Integration

The API uses the `FSMOrchestrator` to handle both new deck creation and modifications.

### New Deck Creation

```python
from v3.fsm.orchestrator import FSMOrchestrator

orchestrator = FSMOrchestrator()

# Prepare request
deck_request = {
    "format": "Standard",
    "colors": ["R", "G"],
    "archetype": "Aggro",
    "strategy": "Build an aggressive red-green deck",
    "quality_threshold": 0.7,
    "max_iterations": 5
}

# Execute FSM
result = await orchestrator.execute(deck_request)

if result["success"]:
    data = result["data"]
    deck = data["deck"]
    quality_metrics = data["quality_metrics"]
    iteration_count = data["iteration_count"]
```

### Deck Modification

```python
from v3.models.deck import Deck, DeckModificationRequest

# Load existing deck
existing_deck = Deck.model_validate(deck_dict)

# Create modification request
mod_request = DeckModificationRequest(
    existing_deck=existing_deck,
    user_prompt="Add more removal spells",
    run_quality_check=False,
    max_changes=10,
    strict_validation=False
)

# Execute modification
result = await orchestrator.execute(mod_request)

if result["success"]:
    modified_deck = result["deck"]
    changes_made = result.get("modifications", {})
```

---

## Error Handling

All endpoints follow a consistent error handling pattern:

```python
try:
    # Perform operation
    result = perform_operation()

    return SuccessResponse(
        success=True,
        data=result,
        error=None
    )

except HTTPException:
    # Re-raise HTTP exceptions
    raise

except Exception as e:
    logger.error(f"Operation error: {str(e)}", exc_info=True)
    return ErrorResponse(
        success=False,
        message="Operation failed",
        error=str(e)
    )
```

**Common HTTP Status Codes:**
- `200 OK`: Successful operation
- `404 Not Found`: Deck not found
- `500 Internal Server Error`: Server-side error

---

## Running the Server

### Development Mode

```bash
# From project root
cd v3
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# From project root
cd v3
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Variables

Create a `.env` file in the v3 directory:

```bash
# LLM Configuration
DEFAULT_MODEL=openai:gpt-4o-mini
OPENAI_API_KEY=your_key_here

# Database
DATABASE_PATH=v3/data/cards.db
DECKS_DATABASE_PATH=v3/data/decks.db

# Logging
LOG_LEVEL=INFO
```

---

## Testing with Python

### Using `requests` library

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a new deck
response = requests.post(
    f"{BASE_URL}/api/chat",
    json={
        "message": "Build a Standard red-green aggro deck",
        "context": None,
        "existing_deck": None
    }
)
result = response.json()
print(result["message"])
deck = result["deck"]

# Save the deck
response = requests.post(
    f"{BASE_URL}/api/decks",
    json={
        "deck": deck,
        "name": "My RG Aggro",
        "description": "Aggressive red-green deck",
        "quality_score": 0.85
    }
)
save_result = response.json()
deck_id = save_result["deck_id"]

# List all decks
response = requests.get(f"{BASE_URL}/api/decks")
decks = response.json()["decks"]

# Get specific deck
response = requests.get(f"{BASE_URL}/api/decks/{deck_id}")
deck_data = response.json()

# Update deck
response = requests.put(
    f"{BASE_URL}/api/decks/{deck_id}",
    json={
        "name": "Updated RG Aggro",
        "quality_score": 0.90
    }
)

# Delete deck
response = requests.delete(f"{BASE_URL}/api/decks/{deck_id}")
```

### Using `httpx` (async)

```python
import httpx
import asyncio

async def test_api():
    async with httpx.AsyncClient() as client:
        # Create deck
        response = await client.post(
            "http://localhost:8000/api/chat",
            json={"message": "Build a Commander Zombie deck"}
        )
        result = response.json()
        print(result["message"])

asyncio.run(test_api())
```

---

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## See Also

- [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) - Frontend integration examples
- [FSM_WORKFLOWS.md](FSM_WORKFLOWS.md) - FSM state machine workflows
- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete system architecture overview
