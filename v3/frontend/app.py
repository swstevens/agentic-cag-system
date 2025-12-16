"""
FastHTML frontend for MTG Deck Builder.

Provides a web interface with deck list and chat components.
"""

import asyncio
import httpx
import os
from pathlib import Path
from fasthtml.common import *
from dotenv import load_dotenv

from components.deck_list import deck_list_component
from components.chat import chat_component, chat_message
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
    get_session_state(session)
    return Title("MTG Deck Builder"), Main(
        render_content(session)
    )

@rt("/chat")
async def post(message: str, session):
    """Handle chat message submission."""
    get_session_state(session)
    
    # Add user message to history
    session["messages"].append({"role": "user", "content": message})
    
    # DEBUG: Test command to verify frontend updating
    if message == "!test_deck":
        print("DEBUG: Executing !test_deck command")
        mock_deck = {
            "format": "Standard",
            "archetype": "Red Deck Wins",
            "total_cards": 4,
            "cards": [
                {"card": {"name": "Mountain", "types": ["Land"], "mana_cost": ""}, "quantity": 2},
                {"card": {"name": "Lightning Bolt", "types": ["Instant"], "mana_cost": "{R}", "cmc": 1}, "quantity": 2}
            ]
        }
        session["deck"] = mock_deck
        session["messages"].append({"role": "assistant", "content": "Debug: Loaded mock deck."})
        print(f"DEBUG: Session deck updated: {session['deck']}")
        return render_content(session)

    try:
        # Call backend API
        print(f"DEBUG: Sending request to {BACKEND_URL}/api/chat")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": message,
                    "context": session.get("context", {})
                }
            )
            response.raise_for_status()
            data = response.json()
            print(f"DEBUG: Received response: {data.keys()}")
        
        # Extract response
        assistant_message = data.get("message", "No response")
        deck_data = data.get("deck")
        error = data.get("error")
        
        print(f"DEBUG: deck_data present: {deck_data is not None}")
        if deck_data:
            print(f"DEBUG: deck_data keys: {deck_data.keys()}")

        # Update session with deck if provided
        if deck_data:
            session["deck"] = deck_data
            # Update context with deck parameters
            session["context"] = {
                "format": deck_data.get("format"),
                "colors": deck_data.get("colors", []),
                "archetype": deck_data.get("archetype"),
            }
            print(f"DEBUG: Session deck updated from backend - Total cards: {deck_data.get('total_cards', 0)}")
            print(f"DEBUG: Session keys after update: {list(session.keys())}")
        
        # Add assistant message to history
        session["messages"].append({"role": "assistant", "content": assistant_message})
        
    except httpx.HTTPError as e:
        error_message = f"Error connecting to backend: {str(e)}"
        print(f"DEBUG: HTTP Error: {e}")
        session["messages"].append({"role": "assistant", "content": error_message})
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        print(f"DEBUG: Exception: {e}")
        session["messages"].append({"role": "assistant", "content": error_message})
    
    # Return the updated main content
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
        print(f"Error loading decks: {e}")
        return Title("My Decks - MTG Deck Builder"), Main(
            Div(
                H1("Error Loading Decks"),
                P(f"Failed to load decks: {str(e)}"),
                A("← Back to Chat", href="/", cls="btn btn-primary"),
                cls="container error-container"
            )
        )


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
        print(f"Error loading deck {deck_id}: {e}")
        session["messages"].append(
            {"role": "assistant", "content": f"Failed to load deck: {str(e)}"}
        )
        return Title("MTG Deck Builder"), Main(
            render_content(session)
        )


@rt("/save-deck-modal")
def get(session):
    """Render the save deck modal."""
    print(f"DEBUG save-deck-modal: Session keys: {list(session.keys())}")
    print(f"DEBUG save-deck-modal: Has deck: {session.get('deck') is not None}")
    if session.get("deck"):
        print(f"DEBUG save-deck-modal: Deck total cards: {session['deck'].get('total_cards', 0)}")

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


@rt("/deck/close-modal")
def get():
    """Close the modal."""
    return Div(id="modal")


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
        print(f"Error saving deck: {e}")
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
        print(f"Error updating deck: {e}")
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
        print(f"Error deleting deck: {e}")
        return Div(
            H1("Error"),
            P(f"Failed to delete deck: {str(e)}"),
            A("← Back to Library", href="/decks", cls="btn btn-primary"),
            cls="container error-container",
            id="main-content"
        )


if __name__ == "__main__":
    import uvicorn
    print("Starting FastHTML frontend on http://localhost:5000")
    print("Make sure FastAPI backend is running on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
