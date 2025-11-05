"""SQLAlchemy ORM models for MTG cards database"""
from sqlalchemy import Column, String, Float, JSON, Index, text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from typing import List, Dict, Optional

Base = declarative_base()


class CardORM(Base):
    """SQLAlchemy ORM model for MTG cards table - mapped to MTGJSON schema"""
    __tablename__ = 'cards'

    # Primary key - MTGJSON uses 'uuid' as primary key
    id = Column('uuid', String, primary_key=True, key='id')

    # Basic card information
    name = Column(String, nullable=False)
    mana_cost = Column('manaCost', String, nullable=True, key='mana_cost')
    cmc = Column('manaValue', Float, default=0.0, key='cmc')

    # JSON columns for complex data types
    # MTGJSON stores these as TEXT (JSON strings), SQLAlchemy will handle conversion
    colors = Column('colors', String, nullable=True, key='colors')  # Stored as comma-separated string
    color_identity = Column('colorIdentity', String, nullable=True, key='color_identity')

    # Type information
    type_line = Column('type', String, nullable=True, key='type_line')
    types = Column('types', String, nullable=True, key='types')  # Stored as comma-separated string
    subtypes = Column('subtypes', String, nullable=True, key='subtypes')  # Stored as comma-separated string

    # Card text and attributes - MTGJSON uses 'text' not 'oracle_text'
    oracle_text = Column('text', String, nullable=True, key='oracle_text')
    power = Column(String, nullable=True)
    toughness = Column(String, nullable=True)
    loyalty = Column(String, nullable=True)

    # Set and rarity
    set_code = Column('setCode', String, nullable=True, key='set_code')
    rarity = Column(String, nullable=True)

    # Keywords - MTGJSON stores as TEXT (comma-separated)
    keywords = Column('keywords', String, nullable=True, key='keywords')

    # Note: Legalities are in a separate table in MTGJSON
    # We'll handle this in the database service layer

    # Define indexes - reference the Column objects, not the database column names
    # Note: MTGJSON database already has indexes, but we define them for completeness
    __table_args__ = (
        Index('idx_name', name),
        Index('idx_setCode', set_code),
        Index('idx_manaValue', cmc),
        Index('idx_rarity', rarity),
    )

    def __repr__(self):
        return f"<CardORM(id='{self.id}', name='{self.name}', set='{self.set_code}')>"

    def to_dict(self) -> dict:
        """Convert ORM model to dictionary for Pydantic conversion"""
        # Helper to parse comma-separated strings to lists
        def parse_list(value: Optional[str]) -> List[str]:
            if not value:
                return []
            # MTGJSON stores as comma-separated values
            return [v.strip() for v in value.split(',') if v.strip()]

        # Use attached legalities if available, otherwise empty dict
        legalities = getattr(self, '_legalities', {})

        return {
            'id': self.id,
            'name': self.name,
            'mana_cost': self.mana_cost,
            'cmc': self.cmc,
            'colors': parse_list(self.colors),
            'color_identity': parse_list(self.color_identity),
            'type_line': self.type_line or '',
            'types': parse_list(self.types),
            'subtypes': parse_list(self.subtypes),
            'oracle_text': self.oracle_text,
            'power': self.power,
            'toughness': self.toughness,
            'loyalty': self.loyalty,
            'set_code': self.set_code or '',
            'rarity': self.rarity or '',
            'legalities': legalities,
            'keywords': parse_list(self.keywords),
        }


class CardLegalitiesORM(Base):
    """SQLAlchemy ORM model for card legalities table - mapped to MTGJSON schema"""
    __tablename__ = 'cardLegalities'

    # Foreign key to cards table
    uuid = Column(String, ForeignKey('cards.uuid'), primary_key=True)

    # Format legalities - MTGJSON stores as individual columns
    alchemy = Column(String, nullable=True)
    brawl = Column(String, nullable=True)
    commander = Column(String, nullable=True)
    duel = Column(String, nullable=True)
    future = Column(String, nullable=True)
    gladiator = Column(String, nullable=True)
    historic = Column(String, nullable=True)
    legacy = Column(String, nullable=True)
    modern = Column(String, nullable=True)
    oathbreaker = Column(String, nullable=True)
    oldschool = Column(String, nullable=True)
    pauper = Column(String, nullable=True)
    paupercommander = Column(String, nullable=True)
    penny = Column(String, nullable=True)
    pioneer = Column(String, nullable=True)
    predh = Column(String, nullable=True)
    premodern = Column(String, nullable=True)
    standard = Column(String, nullable=True)
    standardbrawl = Column(String, nullable=True)
    timeless = Column(String, nullable=True)
    vintage = Column(String, nullable=True)

    def to_dict(self) -> Dict[str, str]:
        """Convert legalities to dictionary format"""
        legalities = {}
        for format_name in ['alchemy', 'brawl', 'commander', 'duel', 'future',
                           'gladiator', 'historic', 'legacy', 'modern', 'oathbreaker',
                           'oldschool', 'pauper', 'paupercommander', 'penny', 'pioneer',
                           'predh', 'premodern', 'standard', 'standardbrawl', 'timeless', 'vintage']:
            value = getattr(self, format_name, None)
            if value:
                legalities[format_name] = value
        return legalities


# Note: FTS5 virtual table will still be managed via raw SQL
# as SQLAlchemy doesn't natively support FTS5 virtual tables
