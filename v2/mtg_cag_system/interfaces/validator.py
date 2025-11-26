"""
Validator interface - defines contract for deck validation strategies.
"""

from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from ..models.card import MTGCard


class ValidationRules(BaseModel):
    """Rules for deck validation"""
    format: str = "Standard"
    max_copies: int = 4
    min_deck_size: int = 60
    max_deck_size: int = 60
    allow_basic_lands: bool = True


class ValidationResult(BaseModel):
    """Result of a validation check"""
    is_valid: bool
    validator_name: str
    messages: List[str] = []
    invalid_cards: List[str] = []
    suggestions: List[str] = []


class IValidator(ABC):
    """
    Interface for deck validators.

    Enables Pipeline Pattern - multiple validators can be chained
    together, each checking a specific aspect of deck legality.
    """

    @abstractmethod
    def validate(
        self,
        cards: List[MTGCard],
        rules: ValidationRules
    ) -> ValidationResult:
        """
        Validate cards against specific rules.

        Args:
            cards: List of cards to validate
            rules: Validation rules to apply

        Returns:
            ValidationResult with validity status and messages
        """
        pass
