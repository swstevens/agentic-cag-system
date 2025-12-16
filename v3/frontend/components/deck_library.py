"""
Deck library component for displaying saved decks.
"""

from fasthtml.common import *
from components.deck_list import deck_list_component


def deck_list_item(deck: dict) -> FT:
    """
    Render a single deck item in the library list.

    Args:
        deck: Deck metadata dictionary

    Returns:
        FastHTML component
    """
    # Format colors
    colors = deck.get("colors", [])
    color_badges = [Span(c, cls=f"color-badge color-{c}") for c in colors]
    if not color_badges:
        color_badges = [Span("C", cls="color-badge color-C")]

    # Format quality score
    quality_score = deck.get("quality_score")
    quality_display = f"{quality_score:.0%}" if quality_score else "N/A"

    return Details(
        Summary(
            Div(
                Div(
                    H3(deck["name"], cls="deck-bar-title"),
                    Span(f"{deck['total_cards']} cards • {quality_display} Quality", cls="deck-bar-meta"),
                    cls="deck-bar-main"
                ),
                Div(
                    Div(
                        Span(f"{deck['format']}", cls="deck-badge"),
                        Span(f"{deck.get('archetype', 'Unknown')}", cls="deck-badge"),
                        *color_badges,
                        cls="deck-bar-badges"
                    ),
                    Div(
                        A(
                            "✏️",
                            href=f"/deck/{deck['id']}",
                            cls="btn-icon",
                            title="Edit Deck"
                        ),
                        Button(
                            "🗑️",
                            hx_delete=f"/deck/{deck['id']}",
                            hx_confirm="Are you sure you want to delete this deck?",
                            hx_target="#main-content",
                            hx_select="#main-content",
                            hx_swap="outerHTML",
                            cls="btn-icon btn-icon-danger",
                            title="Delete Deck"
                        ),
                        cls="deck-bar-actions"
                    ),
                    Span("▶", cls="deck-arrow-icon"),
                    cls="deck-bar-right"
                ),
                cls="deck-bar-content"
            ),
            cls="deck-bar-summary",
            hx_get=f"/deck/{deck['id']}/snippet",
            hx_target=f"#deck-content-{deck['id']}",
            hx_trigger="click once"
        ),
        Div(
            Div(
                P(deck.get("description", "No description"), cls="deck-description-full"),
                cls="deck-details-header"
            ),
            Div(
                P("Loading cards...", cls="loading-text"),
                id=f"deck-content-{deck['id']}",
                cls="deck-card-list-container"
            ),
            cls="deck-expanded-content"
        ),
        cls="deck-bar-item"
    )


def deck_library_component(decks: list, format_filter: str = None, archetype_filter: str = None) -> FT:
    """
    Render the deck library component.

    Args:
        decks: List of deck metadata dictionaries
        format_filter: Current format filter
        archetype_filter: Current archetype filter

    Returns:
        FastHTML component
    """
    # Header with filters
    header = Div(
        H1("My Decks", cls="library-title"),
        Div(
            A("← Back to Chat", href="/", cls="btn btn-secondary"),
            cls="library-actions"
        ),
        cls="library-header"
    )

    # Filters
    formats = ["Standard", "Modern", "Commander", "Pioneer", "Legacy", "Vintage"]
    archetypes = ["Aggro", "Control", "Midrange", "Combo"]

    filters = Form(
        Div(
            Label("Format:", For="format-filter"),
            Select(
                Option("All Formats", value="", selected=(not format_filter)),
                *[Option(f, value=f, selected=(format_filter == f)) for f in formats],
                name="format",
                id="format-filter",
                cls="filter-select"
            ),
            Label("Archetype:", For="archetype-filter"),
            Select(
                Option("All Archetypes", value="", selected=(not archetype_filter)),
                *[Option(a, value=a, selected=(archetype_filter == a)) for a in archetypes],
                name="archetype",
                id="archetype-filter",
                cls="filter-select"
            ),
            Button("Filter", type="submit", cls="btn btn-primary"),
            cls="filter-controls"
        ),
        hx_get="/decks",
        hx_target="#main-content",
        hx_select="#main-content",
        hx_swap="outerHTML",
        cls="library-filters"
    )

    # Deck list
    if decks:
        deck_list = Div(
            *[deck_list_item(deck) for deck in decks],
            cls="deck-library-list"
        )
    else:
        deck_list = Div(
            P("No saved decks found.", cls="empty-state"),
            P("Build a deck in the chat and save it to see it here!", cls="empty-state-hint"),
            A("Start Building →", href="/", cls="btn btn-primary"),
            cls="deck-empty"
        )

    return Div(
        header,
        filters,
        deck_list,
        id="deck-library",
        cls="deck-library-container"
    )
