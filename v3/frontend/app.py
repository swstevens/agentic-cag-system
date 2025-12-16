"""
FastHTML frontend for MTG Deck Builder.

Provides a web interface with deck list and chat components.
"""

import asyncio
import httpx
import os
import logging
from pathlib import Path
import uuid
from fasthtml.common import *
from dotenv import load_dotenv

from components.deck_list import deck_list_component
from components.chat import chat_component, chat_message, thinking_message
from components.deck_library import deck_library_component

# Load environment variables
load_dotenv()

# Initialize FastHTML app with sessions enabled
app, rt = fast_app(
    hdrs=(
        Link(rel="stylesheet", href="/static/styles.css"),
    ),
    live=True,
    pico=False,  # Disable Pico CSS to avoid conflicts
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")  # Enable FastHTML sessions
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Backend API URL
BACKEND_URL = "http://localhost:8000"

@rt("/static/{filepath:path}")
def serve_static(filepath: str):
    """Serve static files."""
    return FileResponse(f"static/{filepath}")


def render_content(session):
    """Render the main content area."""
    has_deck = session.get("deck") is not None
    deck_id = session.get("deck_id")

    return Div(
        deck_list_component(session.get("deck")),
        chat_component(session.get("messages"), has_deck=has_deck, deck_id=deck_id),
        Div(id="modal"),  # Modal container for save dialog
        cls="main-container",
        id="main-content"
    )


def get_session_state(session):
    """Get or initialize session state."""
    if "deck" not in session:
        session["deck"] = None
    if "deck_id" not in session:
        session["deck_id"] = None
    if "messages" not in session:
        session["messages"] = []
    if "context" not in session:
        session["context"] = {}
    return session


@rt("/")
def get(session):
    """Render the main page."""
    # Reset session on full page load
    session.clear()
    get_session_state(session)
    return Title("MTG Deck Builder"), Main(
        render_content(session)
    )

@rt("/chat")
async def post(message: str, session):
    """
    Handle initial chat submission (Fast UI response).
    
    1. Updates session with user message.
    2. Returns:
       - User Message (appended to history)
       - Thinking Indicator (appended to history, triggers processing)
       - Cleared Input (swapped OOB)
    """
    get_session_state(session)
    
    # Add user message to history
    session["messages"].append({"role": "user", "content": message})
    
    # 1. Render User Message
    user_msg_html = chat_message("user", message)
    
    # 2. Render Thinking Indicator with Auto-Trigger
    thinking_html = thinking_message()
    
    # 3. Render Cleared Input (OOB Swap)
    # Replaces the input field with a cleared one to reset the form
    new_input_html = Input(
        type="text",
        name="message",
        placeholder="Type your message...",
        required=True,
        autofocus=True,
        cls="chat-input",
        id="chat-input-field", # Ensure ID matches for specificity if needed, though OOB usually needs ID on target
        hx_swap_oob="true" # This tells HTMX to swap this element by ID
    )
    
    # Return all elements. HTMX will append non-OOB ones to target (#chat-history)
    # and swap OOB ones by ID.
    return user_msg_html, thinking_html, new_input_html


@rt("/chat/process")
async def post(session):
    """
    Handle background chat processing (Heavy backend call).
    
    Triggered by the 'Thinking' indicator loading.
    Returns the full updated content, replacing the temporary state.
    """
    get_session_state(session)
    
    # Get the last message which is the user's prompt
    if not session["messages"] or session["messages"][-1]["role"] != "user":
        # Should not happen in normal flow, but handle gracefully
        return render_content(session)
        
    message = session["messages"][-1]["content"]

    # DEBUG: Test command
    if message == "!test_deck":
        logger.info("Executing !test_deck command")
        mock_deck = {
            "format": "Standard",
            "archetype": "Red Deck Wins",
            "total_cards": 4,
            "cards": [
                {"card": {"id": str(uuid.uuid4()), "name": "Mountain", "types": ["Land"], "type_line": "Basic Land — Mountain", "mana_cost": ""}, "quantity": 2},
                {"card": {"id": str(uuid.uuid4()), "name": "Lightning Bolt", "types": ["Instant"], "type_line": "Instant", "mana_cost": "{R}", "cmc": 1}, "quantity": 2}
            ]
        }
        session["deck"] = mock_deck
        session["deck_id"] = None
        session["messages"].append({"role": "assistant", "content": "Debug: Loaded mock deck."})
        return render_content(session)

    try:
        # Call backend API
        logger.info(f"Sending request to {BACKEND_URL}/api/chat for message: {message}")
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": message,
                    "context": session.get("context", {})
                }
            )
            response.raise_for_status()
            data = response.json()
        
        # Extract response
        assistant_message = data.get("message", "No response")
        deck_data = data.get("deck")
        
        # Update session with deck if provided
        if deck_data:
            session["deck"] = deck_data
            session["context"] = {
                "format": deck_data.get("format"),
                "colors": deck_data.get("colors", []),
                "archetype": deck_data.get("archetype"),
            }
        
        # Add assistant message to history
        session["messages"].append({"role": "assistant", "content": assistant_message})
        
    except httpx.HTTPError as e:
        error_message = f"Error connecting to backend: {str(e)}"
        logger.error(f"HTTP Error: {e}", exc_info=True)
        session["messages"].append({"role": "assistant", "content": error_message})
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(f"Exception: {e}", exc_info=True)
        session["messages"].append({"role": "assistant", "content": error_message})
    
    # Return the updated main content (removes thinking indicator, shows new history)
    return render_content(session)


@rt("/decks")
async def get(session, format: str = "", archetype: str = ""):
    """Render the deck library page."""
    get_session_state(session)

    try:
        # Build query parameters
        params = {}
        if format:
            params["format"] = format
        if archetype:
            params["archetype"] = archetype

        # Fetch saved decks from backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/api/decks",
                params=params
            )
            response.raise_for_status()
            data = response.json()

        decks = data.get("decks", [])

        return Title("My Decks - MTG Deck Builder"), Main(
            Div(
                deck_library_component(decks, format_filter=format, archetype_filter=archetype),
                cls="container",
                id="main-content"
            )
        )

    except Exception as e:
        logger.error(f"Error loading decks: {e}", exc_info=True)
        return Title("My Decks - MTG Deck Builder"), Main(
            Div(
                H1("Error Loading Decks"),
                P(f"Failed to load decks: {str(e)}"),
                A("← Back to Chat", href="/", cls="btn btn-primary"),
                cls="container error-container"
            )
        )


@rt("/deck/close-modal")
def get():
    """Close the modal."""
    return Div(id="modal")


@rt("/deck/{deck_id}")
async def get(deck_id: str, session):
    """Load a specific deck for editing."""
    get_session_state(session)

    try:
        # Fetch deck from backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/decks/{deck_id}")
            response.raise_for_status()
            data = response.json()

        # Load deck into session
        session["deck"] = data["deck"]
        session["deck_id"] = deck_id
        session["messages"] = [
            {"role": "assistant", "content": f"Loaded deck: {data['name']}. You can now modify it by chatting with me!"}
        ]
        session["context"] = {
            "format": data["format"],
            "colors": data.get("colors", []),
            "archetype": data.get("archetype"),
        }

        return Title("MTG Deck Builder"), Main(
            render_content(session)
        )

    except Exception as e:
        logger.error(f"Error loading deck {deck_id}: {e}", exc_info=True)
        session["messages"].append(
            {"role": "assistant", "content": f"Failed to load deck: {str(e)}"}
        )
        return Title("MTG Deck Builder"), Main(
            render_content(session)
        )

@rt("/deck/{deck_id}/snippet")
async def get(deck_id: str, session):
    """Load the card list snippet for lazy loading."""
    get_session_state(session)
    
    try:
        # Fetch deck from backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/decks/{deck_id}")
            response.raise_for_status()
            data = response.json()
        
        from components.deck_list import render_card_groups
        return render_card_groups(data["deck"])

    except Exception as e:
        logger.error(f"Error loading snippet for {deck_id}: {e}", exc_info=True)
        return Div(
            P(f"Failed to load cards: {str(e)}", cls="error-message"),
            cls="deck-expanded-content"
        )


@rt("/save-deck-modal")
def get(session):
    """Render the save deck modal."""
    # logger.debug(f"save-deck-modal: Session keys: {list(session.keys())}")
    # logger.debug(f"save-deck-modal: Has deck: {session.get('deck') is not None}")
    if session.get("deck"):
        pass
        # logger.debug(f"save-deck-modal: Deck total cards: {session['deck'].get('total_cards', 0)}")

    if not session.get("deck"):
        return Div(
            P("No deck to save!", cls="error-message"),
            id="modal"
        )

    # Calculate quality score from deck if available
    quality_score = session.get("deck", {}).get("quality_score", 0.0)

    modal_content = Div(
        Div(
            Div(
                H2("Save Deck"),
                Button(
                    "✕",
                    hx_get="/deck/close-modal",
                    hx_target="#modal",
                    cls="modal-close"
                ),
                cls="modal-header"
            ),
            Form(
                Div(
                    Label("Deck Name:", For="deck-name"),
                    Input(
                        type="text",
                        name="name",
                        id="deck-name",
                        placeholder="Enter deck name...",
                        required=True,
                        cls="form-input"
                    ),
                    cls="form-group"
                ),
                Div(
                    Label("Description (optional):", For="deck-description"),
                    Textarea(
                        name="description",
                        id="deck-description",
                        placeholder="Describe your deck strategy...",
                        rows="3",
                        cls="form-textarea"
                    ),
                    cls="form-group"
                ),
                Div(
                    P(f"Quality Score: {quality_score:.0%}" if quality_score else "Quality Score: Not available"),
                    cls="info-text"
                ),
                Div(
                    Button("Cancel", type="button", hx_get="/deck/close-modal", hx_target="#modal", cls="btn btn-secondary"),
                    Button("Save", type="submit", cls="btn btn-primary"),
                    cls="modal-actions"
                ),
                hx_post="/deck/save",
                hx_target="#modal",
                cls="modal-form"
            ),
            cls="modal-content"
        ),
        cls="modal-overlay",
        id="modal"
    )

    return modal_content





@rt("/deck/save")
async def post(name: str, description: str = "", session = None):
    """Save the current deck."""
    get_session_state(session)

    deck = session.get("deck")
    if not deck:
        return Div(
            P("No deck to save!", cls="error-message"),
            Button("Close", hx_get="/deck/close-modal", hx_target="#modal", cls="btn btn-primary"),
            id="modal"
        )

    try:
        # Get quality score from latest messages or deck data
        quality_score = None
        for msg in reversed(session.get("messages", [])):
            if "Quality Score:" in msg.get("content", ""):
                # Try to extract quality score from message
                try:
                    import re
                    match = re.search(r"Quality Score: (0\.\d+)", msg["content"])
                    if match:
                        quality_score = float(match.group(1))
                        break
                except:
                    pass

        # Save deck to backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/decks",
                json={
                    "deck": deck,
                    "name": name,
                    "description": description,
                    "quality_score": quality_score
                }
            )
            response.raise_for_status()
            data = response.json()

        if data.get("success"):
            # Update session with deck ID
            session["deck_id"] = data["deck_id"]

            return Div(
                Div(
                    H2("Deck Saved!"),
                    P(f"✓ {data['message']}"),
                    Div(
                        Button("Close", hx_get="/deck/close-modal", hx_target="#modal", cls="btn btn-secondary"),
                        A("View My Decks", href="/decks", cls="btn btn-primary"),
                        cls="modal-actions"
                    ),
                    cls="modal-content success-message"
                ),
                cls="modal-overlay",
                id="modal"
            )
        else:
            raise Exception(data.get("error", "Unknown error"))

    except Exception as e:
        logger.error(f"Error saving deck: {e}", exc_info=True)
        return Div(
            Div(
                H2("Save Failed"),
                P(f"❌ Failed to save deck: {str(e)}"),
                Button("Close", hx_get="/deck/close-modal", hx_target="#modal", cls="btn btn-primary"),
                cls="modal-content error-message"
            ),
            cls="modal-overlay",
            id="modal"
        )


@rt("/deck/update")
async def post(session):
    """Update the currently loaded deck."""
    get_session_state(session)

    deck_id = session.get("deck_id")
    deck = session.get("deck")

    if not deck_id or not deck:
        session["messages"].append(
            {"role": "assistant", "content": "No deck loaded to update."}
        )
        return render_content(session)

    try:
        # Update deck in backend
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{BACKEND_URL}/api/decks/{deck_id}",
                json={"deck": deck}
            )
            response.raise_for_status()
            data = response.json()

        if data.get("success"):
            session["messages"].append(
                {"role": "assistant", "content": f"✓ Deck updated successfully!"}
            )
        else:
            raise Exception(data.get("error", "Unknown error"))

    except Exception as e:
        logger.error(f"Error updating deck: {e}", exc_info=True)
        session["messages"].append(
            {"role": "assistant", "content": f"❌ Failed to update deck: {str(e)}"}
        )

    return render_content(session)


@rt("/deck/{deck_id}")
async def delete(deck_id: str):
    """Delete a deck."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(f"{BACKEND_URL}/api/decks/{deck_id}")
            response.raise_for_status()
            data = response.json()

        if data.get("success"):
            # Reload the deck library
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{BACKEND_URL}/api/decks")
                response.raise_for_status()
                decks_data = response.json()

            decks = decks_data.get("decks", [])

            return Div(
                deck_library_component(decks),
                cls="container",
                id="main-content"
            )
        else:
            raise Exception(data.get("error", "Unknown error"))

    except Exception as e:
        logger.error(f"Error deleting deck: {e}", exc_info=True)
        return Div(
            H1("Error"),
            P(f"Failed to delete deck: {str(e)}"),
            A("← Back to Library", href="/decks", cls="btn btn-primary"),
            cls="container error-container",
            id="main-content"
        )


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastHTML frontend on http://localhost:5000")
    logger.info("Make sure FastAPI backend is running on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
