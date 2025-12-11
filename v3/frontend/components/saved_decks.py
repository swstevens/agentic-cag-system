"""
Saved decks page component for viewing and managing saved decks.
"""

from fasthtml.common import *


def saved_deck_item(deck_data: dict, deck_id: int) -> FT:
    """
    Render a single saved deck item.

    Args:
        deck_data: Saved deck dictionary with 'id', 'name', 'deck_data', 'category'
        deck_id: ID of the deck in the database

    Returns:
        FastHTML component
    """
    # Handle both old format (deck) and new format (deck_data)
    deck = deck_data.get("deck_data") or deck_data.get("deck", {})
    total_cards = deck.get("total_cards", 0)
    format_name = deck.get("format", "Unknown")
    archetype = deck.get("archetype", "Unknown")

    return Div(
        Div(
            Div(
                H3(deck_data["name"], cls="saved-deck-name"),
                Div(
                    Span(f"{total_cards} cards", cls="deck-stat"),
                    Span(format_name, cls="deck-stat"),
                    Span(archetype, cls="deck-stat"),
                    Span(deck_data.get("category", "Uncategorized"), cls="deck-category-badge"),
                    cls="saved-deck-info"
                ),
                cls="saved-deck-header"
            ),
            Div(
                Button("Load",
                       hx_post=f"/load_deck/{deck_id}",
                       hx_target="body",
                       hx_swap="outerHTML",
                       cls="deck-action-button load-button"),
                Button("Edit Name",
                       hx_get=f"/edit_deck/{deck_id}",
                       hx_target=f"#saved-deck-{deck_id}",
                       hx_swap="outerHTML",
                       cls="deck-action-button edit-button"),
                Form(
                    Select(
                        Option("Uncategorized", value="Uncategorized"),
                        Option("Aggro", value="Aggro"),
                        Option("Control", value="Control"),
                        Option("Midrange", value="Midrange"),
                        Option("Combo", value="Combo"),
                        Option("Ramp", value="Ramp"),
                        name="category",
                        cls="category-select",
                        value=deck_data.get("category", "Uncategorized")
                    ),
                    Button("Update Category", type="submit", cls="deck-action-button category-button"),
                    hx_post=f"/update_category/{deck_id}",
                    hx_target=f"#saved-deck-{deck_id}",
                    hx_swap="outerHTML",
                    cls="category-form"
                ),
                Button("Delete",
                       hx_delete=f"/delete_deck/{deck_id}",
                       hx_target=f"#saved-deck-{deck_id}",
                       hx_swap="outerHTML",
                       hx_confirm="Are you sure you want to delete this deck?",
                       cls="deck-action-button delete-button"),
                cls="saved-deck-actions"
            ),
            cls="saved-deck-content"
        ),
        id=f"saved-deck-{deck_id}",
        cls="saved-deck-item"
    )


def saved_decks_component(saved_decks: list) -> FT:
    """
    Render the saved decks page.

    Args:
        saved_decks: List of saved deck dictionaries

    Returns:
        FastHTML component
    """
    if not saved_decks:
        content = Div(
            P("No saved decks yet.", cls="empty-state"),
            P("Build and save a deck to see it here!", cls="empty-state-hint"),
            cls="saved-decks-empty"
        )
    else:
        # Use deck ID from backend instead of index
        deck_items = [saved_deck_item(deck, deck["id"]) for deck in saved_decks]
        content = Div(*deck_items, cls="saved-decks-list")

    return Div(
        Div(
            H1("Saved Decks", cls="saved-decks-header"),
            A("← Back to Builder", href="/", cls="back-link"),
            cls="saved-decks-title-section"
        ),
        content,
        cls="saved-decks-container"
    )
