"""
Database interfaces - separates connection management from data loading.
"""

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session


class IConnectionManager(ABC):
    """
    Interface for database connection management.

    Separates connection lifecycle from query execution,
    following Single Responsibility Principle.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if database is connected.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def get_session(self) -> Session:
        """
        Get a database session.

        Returns:
            SQLAlchemy Session object
        """
        pass


class IDataLoader(ABC):
    """
    Interface for loading data from external sources.

    Separates data loading from database operations,
    making it easy to add new data sources (CSV, API, etc.).
    """

    @abstractmethod
    def load_from_source(self, source: str, format: str = "json") -> None:
        """
        Load data from external source into database.

        Args:
            source: Path to data source (file path, URL, etc.)
            format: Data format (json, csv, etc.)
        """
        pass
