"""
Core interface abstractions following Dependency Inversion Principle.

These interfaces define contracts that concrete implementations must follow,
enabling loose coupling and easier testing.
"""

from .agent import IAgent
from .cache import ICache
from .repository import ICardRepository
from .analyzer import IAnalyzer
from .validator import IValidator
from .database import IConnectionManager, IDataLoader

__all__ = [
    "IAgent",
    "ICache",
    "ICardRepository",
    "IAnalyzer",
    "IValidator",
    "IConnectionManager",
    "IDataLoader",
]
