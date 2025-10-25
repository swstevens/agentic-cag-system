"""SQLAlchemy ORM models for MTG cards database"""
from sqlalchemy import Column, String, Float, JSON, Index, text
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Dict, Optional

Base = declarative_base()


class CardORM(Base):
    """SQLAlchemy ORM model for MTG cards table"""
    __tablename__ = 'cards'

    # Primary key
    id = Column(String, primary_key=True)

    # Basic card information
    name = Column(String, nullable=False)
    mana_cost = Column(String, nullable=True)
    cmc = Column(Float, default=0.0)

    # JSON columns for complex data types
    # These will automatically serialize/deserialize Python lists and dicts
    colors = Column(JSON, nullable=True)  # List[str]
    color_identity = Column(JSON, nullable=True)  # List[str]

    # Type information
    type_line = Column(String, nullable=True)
    types = Column(JSON, nullable=True)  # List[str]
    subtypes = Column(JSON, nullable=True)  # List[str]

    # Card text and attributes
    oracle_text = Column(String, nullable=True)
    power = Column(String, nullable=True)
    toughness = Column(String, nullable=True)
    loyalty = Column(String, nullable=True)

    # Set and rarity
    set_code = Column(String, nullable=True)
    rarity = Column(String, nullable=True)

    # Legalities and keywords
    legalities = Column(JSON, nullable=True)  # Dict[str, str]
    keywords = Column(JSON, nullable=True)  # List[str]

    # Define indexes (same as current database)
    __table_args__ = (
        Index('idx_name', 'name'),
        Index('idx_set', 'set_code'),
        Index('idx_cmc', 'cmc'),
        Index('idx_rarity', 'rarity'),
    )

    def __repr__(self):
        return f"<CardORM(id='{self.id}', name='{self.name}', set='{self.set_code}')>"

    def to_dict(self) -> dict:
        """Convert ORM model to dictionary for Pydantic conversion"""
        return {
            'id': self.id,
            'name': self.name,
            'mana_cost': self.mana_cost,
            'cmc': self.cmc,
            'colors': self.colors or [],
            'color_identity': self.color_identity or [],
            'type_line': self.type_line or '',
            'types': self.types or [],
            'subtypes': self.subtypes or [],
            'oracle_text': self.oracle_text,
            'power': self.power,
            'toughness': self.toughness,
            'loyalty': self.loyalty,
            'set_code': self.set_code or '',
            'rarity': self.rarity or '',
            'legalities': self.legalities or {},
            'keywords': self.keywords or [],
        }


# Note: FTS5 virtual table will still be managed via raw SQL
# as SQLAlchemy doesn't natively support FTS5 virtual tables
