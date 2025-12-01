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
        deck_list_component(session.get("deck")),
        chat_component(session.get("messages")),
        cls="container",
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


@rt("/static/{filepath:path}")
def get(filepath: str):
    """Serve static files."""
    return FileResponse(f"static/{filepath}")


if __name__ == "__main__":
    import uvicorn
    print("Starting FastHTML frontend on http://localhost:5000")
    print("Make sure FastAPI backend is running on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
