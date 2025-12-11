"""
Deck list component for displaying cards in the current deck.
"""

from fasthtml.common import *
from components.card import card_component


def deck_list_component(deck: dict | None, saved_decks: list = None) -> FT:
    """
    Render the deck list component.
    
    Args:
        deck: Deck dictionary or None if no deck loaded
        
    Returns:
        FastHTML component
    """
    if not deck or not deck.get("cards"):
        return Div(
            H2("Deck List", cls="deck-header"),
            Div(
                P("No deck loaded yet.", cls="empty-state"),
                P("Start a conversation to build a deck!", cls="empty-state-hint"),
                cls="deck-empty"
            ),
            id="deck-list",
            cls="deck-list-container"
        )
    
    # Group cards by type
    grouped_cards = {}
    for deck_card in deck["cards"]:
        card = deck_card["card"]
        card_types = card.get("types", [])
        
        # Determine primary type
        if "Land" in card_types:
            primary_type = "Lands"
        elif "Creature" in card_types:
            primary_type = "Creatures"
        elif "Instant" in card_types:
            primary_type = "Instants"
        elif "Sorcery" in card_types:
            primary_type = "Sorceries"
        elif "Enchantment" in card_types:
            primary_type = "Enchantments"
        elif "Artifact" in card_types:
            primary_type = "Artifacts"
        elif "Planeswalker" in card_types:
            primary_type = "Planeswalkers"
        else:
            primary_type = "Other"
        
        if primary_type not in grouped_cards:
            grouped_cards[primary_type] = []
        grouped_cards[primary_type].append(deck_card)
    
    # Sort groups in preferred order
    type_order = ["Creatures", "Planeswalkers", "Instants", "Sorceries", "Enchantments", "Artifacts", "Lands", "Other"]
    sorted_groups = [(t, grouped_cards[t]) for t in type_order if t in grouped_cards]
    
    # Build deck info header
    saved_count = len(saved_decks) if saved_decks else 0
    deck_info = Div(
        Div(
            H2("Deck List", cls="deck-header"),
            A(f"View Saved ({saved_count})", href="/decks", cls="view-saved-link"),
            cls="deck-header-row"
        ),
        Div(
            Span(f"{deck['total_cards']} cards", cls="deck-stat"),
            Span(f"{deck['format']}", cls="deck-stat"),
            Span(f"{deck.get('archetype', 'Unknown')}", cls="deck-stat"),
            cls="deck-info"
        ),
        cls="deck-header-section"
    )
    
    # Build card groups
    card_groups = []
    for type_name, cards in sorted_groups:
        card_count = sum(dc["quantity"] for dc in cards)
        
        card_items = []
        for deck_card in sorted(cards, key=lambda x: x["card"]["name"]):
            card = deck_card["card"]
            quantity = deck_card["quantity"]

            # Format mana cost
            mana_cost = card.get("mana_cost", "")
            if not mana_cost and card.get("cmc", 0) > 0:
                mana_cost = f"{{{int(card['cmc'])}}}"

            card_items.append(
                card_component(card["name"], quantity, mana_cost)
            )
        
        card_groups.append(
            Div(
                H3(f"{type_name} ({card_count})", cls="card-type-header"),
                Div(*card_items, cls="card-type-list"),
                cls="card-type-group"
            )
        )
    
    # Save deck form
    save_form = Form(
        Div(
            Input(
                type="text",
                name="deck_name",
                placeholder="Enter deck name...",
                required=True,
                cls="deck-name-input"
            ),
            Button("Save Deck", type="submit", cls="save-deck-button"),
            cls="save-deck-form-group"
        ),
        hx_post="/save_deck",
        hx_target="#deck-list",
        hx_swap="outerHTML",
        cls="save-deck-form"
    )

    return Div(
        deck_info,
        save_form,
        Div(*card_groups, cls="deck-cards"),
        id="deck-list",
        cls="deck-list-container"
    )
