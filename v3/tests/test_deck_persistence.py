"""
Tests for deck persistence functionality.
"""

import pytest
from v3.database.database_service import DatabaseService
from v3.database.deck_repository import DeckRepository
from v3.models.deck import Deck, DeckCard, MTGCard


@pytest.fixture
def db_service():
    """Create a test database service."""
    return DatabaseService(db_path=":memory:")


@pytest.fixture
def deck_repo(db_service):
    """Create a deck repository with test database."""
    return DeckRepository(db_service)


@pytest.fixture
def sample_deck():
    """Create a sample deck for testing."""
    card1 = MTGCard(
        id="test-card-1",
        name="Lightning Bolt",
        mana_cost="{R}",
        cmc=1.0,
        colors=["R"],
        color_identity=["R"],
        type_line="Instant",
        types=["Instant"],
        oracle_text="Lightning Bolt deals 3 damage to any target."
    )

    card2 = MTGCard(
        id="test-card-2",
        name="Mountain",
        type_line="Basic Land — Mountain",
        types=["Land"],
        cmc=0.0
    )

    deck = Deck(
        cards=[
            DeckCard(card=card1, quantity=4),
            DeckCard(card=card2, quantity=20)
        ],
        format="Standard",
        archetype="Aggro",
        colors=["R"]
    )
    deck.calculate_totals()

    return deck


def test_save_deck(deck_repo, sample_deck):
    """Test saving a deck."""
    deck_id = deck_repo.save_deck(
        deck=sample_deck,
        name="Test Deck",
        description="A test deck",
        quality_score=0.85
    )

    assert deck_id is not None
    assert isinstance(deck_id, str)
    assert len(deck_id) > 0


def test_get_deck_by_id(deck_repo, sample_deck):
    """Test retrieving a deck by ID."""
    # Save deck first
    deck_id = deck_repo.save_deck(
        deck=sample_deck,
        name="Test Deck",
        description="A test deck",
        quality_score=0.85
    )

    # Retrieve it
    deck_data = deck_repo.get_deck_by_id(deck_id)

    assert deck_data is not None
    assert deck_data['id'] == deck_id
    assert deck_data['name'] == "Test Deck"
    assert deck_data['format'] == "Standard"
    assert deck_data['archetype'] == "Aggro"
    assert deck_data['quality_score'] == 0.85
    assert deck_data['total_cards'] == 24
    assert deck_data['deck'] is not None


def test_get_nonexistent_deck(deck_repo):
    """Test retrieving a deck that doesn't exist."""
    deck_data = deck_repo.get_deck_by_id("nonexistent-id")
    assert deck_data is None


def test_list_decks(deck_repo, sample_deck):
    """Test listing all decks."""
    # Save multiple decks
    deck_id1 = deck_repo.save_deck(
        deck=sample_deck,
        name="Deck 1",
        quality_score=0.85
    )

    sample_deck.archetype = "Control"
    deck_id2 = deck_repo.save_deck(
        deck=sample_deck,
        name="Deck 2",
        quality_score=0.75
    )

    # List all decks
    decks = deck_repo.list_decks()

    assert len(decks) == 2
    assert any(d['id'] == deck_id1 for d in decks)
    assert any(d['id'] == deck_id2 for d in decks)


def test_list_decks_with_format_filter(deck_repo, sample_deck):
    """Test listing decks with format filter."""
    # Save decks with different formats
    deck_repo.save_deck(
        deck=sample_deck,
        name="Standard Deck"
    )

    sample_deck.format = "Modern"
    deck_repo.save_deck(
        deck=sample_deck,
        name="Modern Deck"
    )

    # Filter by Standard
    standard_decks = deck_repo.list_decks(format_filter="Standard")
    assert len(standard_decks) == 1
    assert standard_decks[0]['format'] == "Standard"

    # Filter by Modern
    modern_decks = deck_repo.list_decks(format_filter="Modern")
    assert len(modern_decks) == 1
    assert modern_decks[0]['format'] == "Modern"


def test_list_decks_with_archetype_filter(deck_repo, sample_deck):
    """Test listing decks with archetype filter."""
    # Save decks with different archetypes
    deck_repo.save_deck(
        deck=sample_deck,
        name="Aggro Deck"
    )

    sample_deck.archetype = "Control"
    deck_repo.save_deck(
        deck=sample_deck,
        name="Control Deck"
    )

    # Filter by Aggro
    aggro_decks = deck_repo.list_decks(archetype_filter="Aggro")
    assert len(aggro_decks) == 1
    assert aggro_decks[0]['archetype'] == "Aggro"

    # Filter by Control
    control_decks = deck_repo.list_decks(archetype_filter="Control")
    assert len(control_decks) == 1
    assert control_decks[0]['archetype'] == "Control"


def test_update_deck(deck_repo, sample_deck):
    """Test updating a deck."""
    # Save initial deck
    deck_id = deck_repo.save_deck(
        deck=sample_deck,
        name="Initial Name",
        quality_score=0.5
    )

    # Update the deck
    sample_deck.archetype = "Midrange"
    updated = deck_repo.update_deck(
        deck_id=deck_id,
        deck=sample_deck,
        name="Updated Name",
        quality_score=0.9
    )

    assert updated is True

    # Verify changes
    deck_data = deck_repo.get_deck_by_id(deck_id)
    assert deck_data['name'] == "Updated Name"
    assert deck_data['archetype'] == "Midrange"
    assert deck_data['quality_score'] == 0.9


def test_update_nonexistent_deck(deck_repo, sample_deck):
    """Test updating a deck that doesn't exist."""
    updated = deck_repo.update_deck(
        deck_id="nonexistent-id",
        deck=sample_deck
    )
    assert updated is False


def test_delete_deck(deck_repo, sample_deck):
    """Test deleting a deck."""
    # Save deck
    deck_id = deck_repo.save_deck(
        deck=sample_deck,
        name="Deck to Delete"
    )

    # Delete it
    deleted = deck_repo.delete_deck(deck_id)
    assert deleted is True

    # Verify it's gone
    deck_data = deck_repo.get_deck_by_id(deck_id)
    assert deck_data is None


def test_delete_nonexistent_deck(deck_repo):
    """Test deleting a deck that doesn't exist."""
    deleted = deck_repo.delete_deck("nonexistent-id")
    assert deleted is False


def test_get_deck_count(deck_repo, sample_deck):
    """Test getting deck count."""
    # Initially empty
    assert deck_repo.get_deck_count() == 0

    # Save some decks
    deck_repo.save_deck(deck=sample_deck, name="Deck 1")
    deck_repo.save_deck(deck=sample_deck, name="Deck 2")

    assert deck_repo.get_deck_count() == 2


def test_get_deck_count_with_filters(deck_repo, sample_deck):
    """Test getting deck count with filters."""
    # Save decks with different formats
    deck_repo.save_deck(deck=sample_deck, name="Standard 1")
    deck_repo.save_deck(deck=sample_deck, name="Standard 2")

    sample_deck.format = "Modern"
    deck_repo.save_deck(deck=sample_deck, name="Modern 1")

    # Count all
    assert deck_repo.get_deck_count() == 3

    # Count by format
    assert deck_repo.get_deck_count(format_filter="Standard") == 2
    assert deck_repo.get_deck_count(format_filter="Modern") == 1


def test_pagination(deck_repo, sample_deck):
    """Test pagination in list_decks."""
    # Save 5 decks
    for i in range(5):
        deck_repo.save_deck(deck=sample_deck, name=f"Deck {i}")

    # Get first 2
    page1 = deck_repo.list_decks(limit=2, offset=0)
    assert len(page1) == 2

    # Get next 2
    page2 = deck_repo.list_decks(limit=2, offset=2)
    assert len(page2) == 2

    # Verify they're different
    assert page1[0]['id'] != page2[0]['id']
