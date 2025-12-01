"""
FastAPI backend for MTG deck building system.

Exposes REST API endpoints that wrap the FSM orchestrator.
"""

import asyncio
import re
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from v3.fsm.orchestrator import FSMOrchestrator
from v3.models.deck import Deck


# Request/Response Models
class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str
    deck: Optional[Dict[str, Any]] = None
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

# Initialize orchestrator
orchestrator = FSMOrchestrator()


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
            "health": "/health"
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
    
    Args:
        request: Chat request with message and optional context
        
    Returns:
        Chat response with message, deck data, and any errors
    """
    try:
        # Parse the user's message
        deck_request = parse_deck_request(request.message, request.context)
        print(f"DEBUG: Parsed request: {deck_request}")
        
        # Execute FSM orchestrator
        result = await orchestrator.execute(deck_request)
        print(f"DEBUG: FSM Result success: {result['success']}")
        if not result['success']:
             print(f"DEBUG: FSM Error: {result.get('error')}")
             print(f"DEBUG: FSM Errors list: {result.get('errors')}")
        
        # Check if successful
        if result["success"]:
            data = result["data"]
            deck_dict = data["deck"]
            print(f"DEBUG: Deck built: {deck_dict.get('archetype')} - {deck_dict.get('total_cards')} cards")
            quality_metrics = data["quality_metrics"]
            
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
                for issue in quality_metrics["issues"][:3]:  # Limit to 3
                    message_parts.append(f"  - {issue}")
            
            if quality_metrics.get("suggestions"):
                message_parts.append("\n💡 Suggestions:")
                for suggestion in quality_metrics["suggestions"][:3]:  # Limit to 3
                    message_parts.append(f"  - {suggestion}")
            
            response_message = "\n".join(message_parts)
            
            return ChatResponse(
                message=response_message,
                deck=deck_dict,
                error=None
            )
        else:
            # Handle failure
            error_msg = result.get("error", "Unknown error occurred")
            return ChatResponse(
                message=f"❌ Failed to build deck: {error_msg}",
                deck=None,
                error=error_msg
            )
            
    except Exception as e:
        # Handle unexpected errors
        error_msg = str(e)
        return ChatResponse(
            message=f"❌ An error occurred: {error_msg}",
            deck=None,
            error=error_msg
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
