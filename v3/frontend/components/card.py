"""
Card component for displaying individual cards in the deck list.
"""

from fasthtml.common import *


def card_component(card_name: str, quantity: int, mana_cost: str = "") -> FT:
    """
    Render a single card item.

    Args:
        card_name: Name of the card
        quantity: Number of copies in the deck
        mana_cost: Mana cost (e.g., "{R}{G}" or "{3}")

    Returns:
        FastHTML component
    """
    return Div(
        Span(f"{quantity}x", cls="card-quantity"),
        Span(card_name, cls="card-name"),
        Span(mana_cost, cls="card-mana-cost"),
        cls="card-item"
    )
