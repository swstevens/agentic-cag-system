"""
Repository implementations following Repository Pattern.

Repositories abstract data access behind clean interfaces,
making the codebase more testable and maintainable.
"""

from .card_repository import CardRepository

__all__ = ["CardRepository"]
