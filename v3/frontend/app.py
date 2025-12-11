"""
FastHTML frontend for MTG Deck Builder.

Provides a web interface with deck list and chat components.
"""

import asyncio
import httpx
from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware

from components.deck_list import deck_list_component
from components.chat import chat_component, chat_message
from components.saved_decks import saved_decks_component, saved_deck_item


# Initialize FastHTML app
app, rt = fast_app(
    hdrs=(
        Link(rel="stylesheet", href="/static/styles.css"),
    ),
    live=True
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here-change-in-production")

# Backend API URL
BACKEND_URL = "http://localhost:8000"


def render_content(session):
    """Render the main content area."""
    return Div(
        deck_list_component(session.get("deck"), session.get("saved_decks", [])),
        chat_component(session.get("messages")),
        cls="main-container",
        id="main-content"
    )


def get_session_state(session):
    """Get or initialize session state."""
    if "deck" not in session:
        session["deck"] = None
    if "messages" not in session:
        session["messages"] = []
    if "context" not in session:
        session["context"] = {}
    if "saved_decks" not in session:
        session["saved_decks"] = []
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
            print("DEBUG: Session deck updated from backend")
        
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


@rt("/save_deck")
async def post(deck_name: str, session):
    """Handle saving the current deck."""
    get_session_state(session)

    current_deck = session.get("deck")
    if not current_deck:
        # No deck to save
        return deck_list_component(None, session.get("saved_decks", []))

    # Create a saved deck entry
    saved_deck = {
        "name": deck_name,
        "deck": current_deck.copy(),
        "category": "Uncategorized",
        "created_at": None  # Could add timestamp if needed
    }

    # Add to saved decks
    if "saved_decks" not in session:
        session["saved_decks"] = []
    session["saved_decks"].append(saved_deck)

    # Return updated deck list
    return deck_list_component(current_deck, session["saved_decks"])


@rt("/decks")
def get(session):
    """Render the saved decks page."""
    get_session_state(session)
    return Title("Saved Decks - MTG Deck Builder"), Main(
        saved_decks_component(session.get("saved_decks", []))
    )


@rt("/load_deck/{index}")
async def post(index: int, session):
    """Load a saved deck into the current deck."""
    get_session_state(session)

    saved_decks = session.get("saved_decks", [])
    if 0 <= index < len(saved_decks):
        # Load the deck
        session["deck"] = saved_decks[index]["deck"].copy()
        # Update context
        deck_data = session["deck"]
        session["context"] = {
            "format": deck_data.get("format"),
            "colors": deck_data.get("colors", []),
            "archetype": deck_data.get("archetype"),
        }
        # Add a message to chat
        session["messages"].append({
            "role": "assistant",
            "content": f"Loaded deck: {saved_decks[index]['name']}"
        })

    # Return to main page
    return Title("MTG Deck Builder"), Main(
        render_content(session)
    )


@rt("/edit_deck/{index}")
def get(index: int, session):
    """Render edit form for a deck name."""
    get_session_state(session)

    saved_decks = session.get("saved_decks", [])
    if 0 <= index < len(saved_decks):
        deck_data = saved_decks[index]
        return Div(
            Form(
                Input(
                    type="text",
                    name="new_name",
                    value=deck_data["name"],
                    required=True,
                    cls="deck-name-edit-input"
                ),
                Button("Save", type="submit", cls="deck-action-button save-button"),
                Button("Cancel",
                       hx_get=f"/cancel_edit/{index}",
                       hx_target=f"#saved-deck-{index}",
                       hx_swap="outerHTML",
                       cls="deck-action-button cancel-button"),
                hx_post=f"/save_edit/{index}",
                hx_target=f"#saved-deck-{index}",
                hx_swap="outerHTML",
                cls="edit-deck-form"
            ),
            id=f"saved-deck-{index}",
            cls="saved-deck-item editing"
        )
    return Div()  # Return empty if index invalid


@rt("/save_edit/{index}")
async def post(index: int, new_name: str, session):
    """Save edited deck name."""
    get_session_state(session)

    saved_decks = session.get("saved_decks", [])
    if 0 <= index < len(saved_decks):
        saved_decks[index]["name"] = new_name
        session["saved_decks"] = saved_decks
        return saved_deck_item(saved_decks[index], index)
    return Div()


@rt("/cancel_edit/{index}")
def get(index: int, session):
    """Cancel editing and return to normal view."""
    get_session_state(session)

    saved_decks = session.get("saved_decks", [])
    if 0 <= index < len(saved_decks):
        return saved_deck_item(saved_decks[index], index)
    return Div()


@rt("/update_category/{index}")
async def post(index: int, category: str, session):
    """Update deck category."""
    get_session_state(session)

    saved_decks = session.get("saved_decks", [])
    if 0 <= index < len(saved_decks):
        saved_decks[index]["category"] = category
        session["saved_decks"] = saved_decks
        return saved_deck_item(saved_decks[index], index)
    return Div()


@rt("/delete_deck/{index}")
async def delete(index: int, session):
    """Delete a saved deck."""
    get_session_state(session)

    saved_decks = session.get("saved_decks", [])
    if 0 <= index < len(saved_decks):
        del saved_decks[index]
        session["saved_decks"] = saved_decks

    # Return empty - the item will be removed from the DOM
    return Div()


@rt("/static/{filepath:path}")
def get(filepath: str):
    """Serve static files."""
    return FileResponse(f"static/{filepath}")


if __name__ == "__main__":
    import uvicorn
    print("Starting FastHTML frontend on http://localhost:5000")
    print("Make sure FastAPI backend is running on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
