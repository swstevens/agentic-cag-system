"""
Deck library component for displaying saved decks.
"""

from fasthtml.common import *


def deck_card_item(deck: dict) -> FT:
    """
    Render a single deck card in the library grid.

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

    # Format date
    created_at = deck.get("created_at", "")
    if created_at and "T" in created_at:
        created_at = created_at.split("T")[0]

    return Div(
        Div(
            H3(deck["name"], cls="deck-card-title"),
            P(deck.get("description", "No description"), cls="deck-card-description"),
            Div(
                Span(f"{deck['format']}", cls="deck-badge"),
                Span(f"{deck.get('archetype', 'Unknown')}", cls="deck-badge"),
                *color_badges,
                cls="deck-badges"
            ),
            Div(
                Span(f"{deck['total_cards']} cards", cls="deck-stat-item"),
                Span(f"Quality: {quality_display}", cls="deck-stat-item"),
                cls="deck-stats"
            ),
            Div(
                A(
                    "✏️ Edit",
                    href=f"/deck/{deck['id']}",
                    cls="btn btn-sm btn-primary"
                ),
                Button(
                    "🗑️ Delete",
                    hx_delete=f"/deck/{deck['id']}",
                    hx_confirm="Are you sure you want to delete this deck?",
                    hx_target="#main-content",
                    hx_swap="outerHTML",
                    cls="btn btn-sm btn-danger"
                ),
                cls="deck-card-actions"
            ),
            cls="deck-card-content"
        ),
        cls="deck-card"
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
        hx_swap="outerHTML",
        cls="library-filters"
    )

    # Deck grid
    if decks:
        deck_grid = Div(
            *[deck_card_item(deck) for deck in decks],
            cls="deck-grid"
        )
    else:
        deck_grid = Div(
            P("No saved decks found.", cls="empty-state"),
            P("Build a deck in the chat and save it to see it here!", cls="empty-state-hint"),
            A("Start Building →", href="/", cls="btn btn-primary"),
            cls="deck-empty"
        )

    return Div(
        header,
        filters,
        deck_grid,
        id="deck-library",
        cls="deck-library-container"
    )
