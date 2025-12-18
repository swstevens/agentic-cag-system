"""
FastAPI backend for MTG deck building system.

Exposes REST API endpoints that wrap the FSM orchestrator.
"""

import asyncio
import re
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from v3.fsm.orchestrator import FSMOrchestrator
from v3.models.deck import Deck, DeckModificationRequest
from v3.database.deck_repository import DeckRepository
from v3.database.database_service import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Request/Response Models
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


# Initialize FastAPI app
app = FastAPI(
    title="MTG Deck Builder API",
    description="REST API for building Magic: The Gathering decks using FSM orchestrator",
    version="3.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator and repositories
orchestrator = FSMOrchestrator()
db_service = DatabaseService()
deck_repository = DeckRepository(db_service)


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
    
    # Determine if this is a new deck or refinement request
    is_new_deck = any(keyword in message_lower for keyword in ["build", "create", "new deck", "make"])
    is_refinement = any(keyword in message_lower for keyword in ["refine", "improve", "change", "modify", "adjust"])
    
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
    
    # If no colors specified, default to colorless or use context
    if not colors and context and "colors" in context:
        colors = context["colors"]
    elif not colors:
        colors = ["R"]  # default to red
    
    # Extract archetype
    archetype_map = {
        "aggro": "Aggro",
        "control": "Control",
        "midrange": "Midrange",
        "combo": "Combo",
    }
    archetype = None
    for key, value in archetype_map.items():
        if key in message_lower:
            archetype = value
            break
    
    # Use context archetype if not specified
    if not archetype and context and "archetype" in context:
        archetype = context["archetype"]
    elif not archetype:
        archetype = "Aggro"  # default
    
    # Build request
    request = {
        "format": format_name,
        "colors": colors,
        "archetype": archetype,
        "strategy": message,  # Use full message as strategy description
        "quality_threshold": 0.7,
        "max_iterations": 5,
        "deck_size": 60,
    }
    
    return request


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MTG Deck Builder API",
        "version": "3.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/health",
            "decks": {
                "list": "GET /api/decks",
                "get": "GET /api/decks/{id}",
                "save": "POST /api/decks",
                "update": "PUT /api/decks/{id}",
                "delete": "DELETE /api/decks/{id}"
            }
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


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

                response_message = f"✓ Deck modified!\n{modifications.get('summary', '')}"
                if modifications.get('quality_after'):
                    response_message += f"\nQuality Score: {modifications['quality_after']:.2f}"

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
            logger.info(f"Parsed request: {deck_request}")

            result = await orchestrator.execute(deck_request)
            logger.info(f"FSM Result success: {result['success']}")

            if result["success"]:
                data = result["data"]
                deck_dict = data["deck"]
                logger.info(f"Deck built: {deck_dict.get('archetype')} - {deck_dict.get('total_cards')} cards")
                quality_metrics = data["quality_metrics"]

                # Add quality score to deck dict for frontend
                deck_dict["quality_score"] = quality_metrics["overall_score"]

                # Format response message
                message_parts = [
                    f"✓ Successfully built a {deck_dict['archetype']} deck!",
                    f"\nQuality Score: {quality_metrics['overall_score']:.2f}",
                    f"Iterations: {data['iteration_count']}",
                    f"Total Cards: {deck_dict['total_cards']}",
                ]

                # Add quality breakdown
                if quality_metrics.get("issues"):
                    message_parts.append("\n⚠ Issues:")
                    for issue in quality_metrics["issues"][:3]:
                        message_parts.append(f"  - {issue}")

                if quality_metrics.get("suggestions"):
                    message_parts.append("\n💡 Suggestions:")
                    for suggestion in quality_metrics["suggestions"][:3]:
                        message_parts.append(f"  - {suggestion}")

                response_message = "\n".join(message_parts)

                return ChatResponse(
                    message=response_message,
                    deck=deck_dict,
                    error=None
                )
            else:
                error_msg = result.get("error", "Unknown error occurred")
                return ChatResponse(
                    message=f"❌ Failed to build deck: {error_msg}",
                    deck=None,
                    error=error_msg
                )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return ChatResponse(
            message=f"❌ An error occurred: {error_msg}",
            deck=None,
            error=error_msg
        )


@app.post("/api/decks", response_model=SaveDeckResponse)
async def save_deck(request: SaveDeckRequest) -> SaveDeckResponse:
    """
    Save a new deck to the database.

    Args:
        request: Save deck request with deck data and metadata

    Returns:
        Response with deck ID and success status
    """
    try:
        # Parse and validate deck
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
        error_msg = str(e)
        logger.error(f"Error saving deck: {e}", exc_info=True)
        return SaveDeckResponse(
            success=False,
            deck_id=None,
            message="Failed to save deck",
            error=error_msg
        )


@app.get("/api/decks", response_model=DeckListResponse)
async def list_decks(
    format: Optional[str] = None,
    archetype: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> DeckListResponse:
    """
    List all saved decks with optional filters.

    Args:
        format: Optional format filter (e.g., "Standard", "Commander")
        archetype: Optional archetype filter (e.g., "Aggro", "Control")
        limit: Maximum results to return (default: 100)
        offset: Number of results to skip for pagination (default: 0)

    Returns:
        Response with list of decks and total count
    """
    try:
        # Get decks from repository
        decks = deck_repository.list_decks(
            format_filter=format,
            archetype_filter=archetype,
            limit=limit,
            offset=offset
        )

        # Get total count
        total = deck_repository.get_deck_count(
            format_filter=format,
            archetype_filter=archetype
        )

        # Convert to list items
        deck_items = [
            DeckListItem(
                id=deck['id'],
                name=deck['name'],
                description=deck.get('description'),
                format=deck['format'],
                archetype=deck.get('archetype'),
                colors=deck.get('colors', []),
                total_cards=deck.get('total_cards', 0),
                quality_score=deck.get('quality_score'),
                created_at=deck.get('created_at', ''),
                updated_at=deck.get('updated_at', '')
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
        error_msg = str(e)
        logger.error(f"Error listing decks: {e}", exc_info=True)
        return DeckListResponse(
            success=False,
            decks=[],
            total=0,
            error=error_msg
        )


@app.get("/api/decks/{deck_id}")
async def get_deck(deck_id: str) -> Dict[str, Any]:
    """
    Get a specific deck by ID.

    Args:
        deck_id: Deck UUID

    Returns:
        Deck data with metadata
    """
    try:
        deck_data = deck_repository.get_deck_by_id(deck_id)

        if not deck_data:
            raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")

        return {
            "success": True,
            "deck_id": deck_data['id'],
            "name": deck_data['name'],
            "description": deck_data.get('description'),
            "format": deck_data['format'],
            "archetype": deck_data.get('archetype'),
            "colors": deck_data.get('colors', []),
            "total_cards": deck_data.get('total_cards', 0),
            "quality_score": deck_data.get('quality_score'),
            "deck": deck_data.get('deck'),
            "created_at": deck_data.get('created_at'),
            "updated_at": deck_data.get('updated_at'),
            "error": None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deck {deck_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/decks/{deck_id}", response_model=UpdateDeckResponse)
async def update_deck(deck_id: str, request: UpdateDeckRequest) -> UpdateDeckResponse:
    """
    Update an existing deck.

    Args:
        deck_id: Deck UUID
        request: Update request with deck data and optional metadata

    Returns:
        Response with success status
    """
    try:
        # Parse and validate deck
        deck = Deck.model_validate(request.deck)

        # Update in database
        updated = deck_repository.update_deck(
            deck_id=deck_id,
            deck=deck,
            name=request.name,
            description=request.description,
            quality_score=request.quality_score
        )

        if not updated:
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
        error_msg = str(e)
        logger.error(f"Error updating deck {deck_id}: {e}", exc_info=True)
        return UpdateDeckResponse(
            success=False,
            message="Failed to update deck",
            error=error_msg
        )


@app.delete("/api/decks/{deck_id}", response_model=DeleteDeckResponse)
async def delete_deck(deck_id: str) -> DeleteDeckResponse:
    """
    Delete a deck by ID.

    Args:
        deck_id: Deck UUID

    Returns:
        Response with success status
    """
    try:
        deleted = deck_repository.delete_deck(deck_id)

        if not deleted:
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
        error_msg = str(e)
        logger.error(f"Error deleting deck {deck_id}: {e}", exc_info=True)
        return DeleteDeckResponse(
            success=False,
            message="Failed to delete deck",
            error=error_msg
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
