"""Utilities to convert between SQLAlchemy ORM and Pydantic models"""
from typing import List, Optional
from mtg_cag_system.models.card import MTGCard, CardColor, CardType
from mtg_cag_system.models.card_orm import CardORM


def orm_to_pydantic(card_orm: CardORM) -> MTGCard:
    """
    Convert SQLAlchemy ORM CardORM to Pydantic MTGCard

    Args:
        card_orm: SQLAlchemy ORM model instance

    Returns:
        Pydantic MTGCard instance
    """
    # Convert the ORM model to dict first
    data = card_orm.to_dict()

    # Pydantic will handle validation and enum conversion
    return MTGCard(**data)


def pydantic_to_orm(card: MTGCard) -> CardORM:
    """
    Convert Pydantic MTGCard to SQLAlchemy ORM CardORM

    Args:
        card: Pydantic MTGCard instance

    Returns:
        SQLAlchemy ORM CardORM instance
    """
    # Use model_dump to get dict representation with enum values
    data = card.model_dump()

    # Create ORM instance from the dict
    # SQLAlchemy will handle the JSON serialization for list/dict fields
    return CardORM(**data)


def orm_list_to_pydantic(cards_orm: List[CardORM]) -> List[MTGCard]:
    """
    Convert list of SQLAlchemy ORM models to Pydantic models

    Args:
        cards_orm: List of SQLAlchemy ORM model instances

    Returns:
        List of Pydantic MTGCard instances
    """
    return [orm_to_pydantic(card) for card in cards_orm]


def pydantic_list_to_orm(cards: List[MTGCard]) -> List[CardORM]:
    """
    Convert list of Pydantic models to SQLAlchemy ORM models

    Args:
        cards: List of Pydantic MTGCard instances

    Returns:
        List of SQLAlchemy ORM CardORM instances
    """
    return [pydantic_to_orm(card) for card in cards]
