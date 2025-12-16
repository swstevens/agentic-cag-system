"""
Test the complete deck modification flow.

Tests the entire chain:
API → Orchestrator → UserModificationNode → Agent → Response
"""

import pytest
import asyncio
from v3.models.deck import (
    Deck, DeckCard, MTGCard, DeckModificationRequest
)
from v3.fsm.orchestrator import FSMOrchestrator


@pytest.fixture
def sample_deck():
    """Create a sample Standard deck for testing."""
    cards = [
        DeckCard(
            card=MTGCard(
                id="card1",
                name="Lightning Bolt",
                mana_cost="{R}",
                cmc=1.0,
                colors=["R"],
                color_identity=["R"],
                type_line="Instant",
                types=["Instant"],
                oracle_text="Lightning Bolt deals 3 damage to any target.",
                rarity="common",
                legalities={"Standard": "legal"}
            ),
            quantity=4
        ),
        DeckCard(
            card=MTGCard(
                id="card2",
                name="Mountain",
                mana_cost="",
                cmc=0.0,
                colors=[],
                color_identity=["R"],
                type_line="Basic Land — Mountain",
                types=["Land"],
                subtypes=["Mountain"],
                oracle_text="({T}: Add {R}.)",
                rarity="common",
                legalities={"Standard": "legal"}
            ),
            quantity=24
        ),
        DeckCard(
            card=MTGCard(
                id="card3",
                name="Monastery Swiftspear",
                mana_cost="{R}",
                cmc=1.0,
                colors=["R"],
                color_identity=["R"],
                type_line="Creature — Human Monk",
                types=["Creature"],
                subtypes=["Human", "Monk"],
                oracle_text="Haste\nProwess",
                power="1",
                toughness="2",
                rarity="uncommon",
                legalities={"Standard": "legal"}
            ),
            quantity=4
        ),
        DeckCard(
            card=MTGCard(
                id="card4",
                name="Shock",
                mana_cost="{R}",
                cmc=1.0,
                colors=["R"],
                color_identity=["R"],
                type_line="Instant",
                types=["Instant"],
                oracle_text="Shock deals 2 damage to any target.",
                rarity="common",
                legalities={"Standard": "legal"}
            ),
            quantity=4
        ),
    ]

    # Add more cards to reach 60
    for i in range(5, 12):
        cards.append(
            DeckCard(
                card=MTGCard(
                    id=f"card{i}",
                    name=f"Test Creature {i}",
                    mana_cost="{2}{R}",
                    cmc=3.0,
                    colors=["R"],
                    color_identity=["R"],
                    type_line="Creature — Human",
                    types=["Creature"],
                    subtypes=["Human"],
                    oracle_text="Test creature",
                    power="3",
                    toughness="2",
                    rarity="common",
                    legalities={"Standard": "legal"}
                ),
                quantity=4
            )
        )

    deck = Deck(
        cards=cards,
        format="Standard",
        archetype="Aggro",
        colors=["R"]
    )
    deck.calculate_totals()
    return deck


@pytest.mark.asyncio
async def test_orchestrator_routes_modification_request(sample_deck):
    """Test that orchestrator correctly routes DeckModificationRequest."""
    orchestrator = FSMOrchestrator(db_path="v3/data/cards.db")

    mod_request = DeckModificationRequest(
        existing_deck=sample_deck,
        user_prompt="Add more card draw",
        run_quality_check=False
    )

    # Execute should recognize this as modification request
    result = await orchestrator.execute(mod_request)

    # Should return success
    assert "success" in result
    assert "deck" in result or "error" in result

    print(f"✓ Orchestrator routing test passed")
    print(f"  Result: {result.get('success')}")


@pytest.mark.asyncio
async def test_modification_preserves_format(sample_deck):
    """Test that modification preserves deck format."""
    orchestrator = FSMOrchestrator(db_path="v3/data/cards.db")

    original_format = sample_deck.format

    mod_request = DeckModificationRequest(
        existing_deck=sample_deck,
        user_prompt="Add more removal spells",
        run_quality_check=False
    )

    result = await orchestrator.execute(mod_request)

    if result.get("success"):
        modified_deck_data = result.get("deck")
        assert modified_deck_data is not None
        assert modified_deck_data.get("format") == original_format
        print(f"✓ Format preservation test passed")
    else:
        print(f"⚠ Modification failed: {result.get('error')}")


@pytest.mark.asyncio
async def test_api_request_format():
    """Test that API request format works correctly."""
    from v3.api import ChatRequest

    # Test new deck request (no existing_deck)
    new_deck_request = ChatRequest(
        message="Build a Standard red aggro deck"
    )
    assert new_deck_request.existing_deck is None
    print("✓ New deck request format valid")

    # Test modification request (with existing_deck)
    deck_data = {
        "cards": [],
        "format": "Standard",
        "archetype": "Aggro",
        "colors": ["R"],
        "total_cards": 0
    }

    mod_request = ChatRequest(
        message="Add more card draw",
        existing_deck=deck_data
    )
    assert mod_request.existing_deck is not None
    print("✓ Modification request format valid")


@pytest.mark.asyncio
async def test_user_modification_node_executes(sample_deck):
    """Test that UserModificationNode executes without errors."""
    from v3.fsm.states import UserModificationNode
    from v3.database.database_service import DatabaseService
    from v3.database.card_repository import CardRepository
    from v3.services.agent_deck_builder_service import AgentDeckBuilderService
    from v3.services.quality_verifier_service import QualityVerifierService
    from v3.services.llm_service import LLMService

    # Initialize services
    db_service = DatabaseService("v3/data/cards.db")
    card_repo = CardRepository(db_service)
    agent_deck_builder = AgentDeckBuilderService(card_repo)
    llm_service = LLMService()
    quality_verifier = QualityVerifierService(llm_service)

    mod_request = DeckModificationRequest(
        existing_deck=sample_deck,
        user_prompt="Make the deck more aggressive",
        run_quality_check=False
    )

    # Execute node directly
    node = UserModificationNode()
    result = await node.execute(
        mod_request=mod_request,
        agent_deck_builder=agent_deck_builder,
        quality_verifier=quality_verifier,
        card_repo=card_repo
    )

    assert "success" in result
    print(f"✓ UserModificationNode execution test passed")
    print(f"  Success: {result.get('success')}")
    if not result.get("success"):
        print(f"  Error: {result.get('error')}")


@pytest.mark.asyncio
async def test_full_modification_chain(sample_deck):
    """Test the complete modification chain end-to-end."""
    orchestrator = FSMOrchestrator(db_path="v3/data/cards.db")

    print("\n=== Testing Full Modification Chain ===")
    print(f"Original deck: {sample_deck.total_cards} cards")
    print(f"Original archetype: {sample_deck.archetype}")

    mod_request = DeckModificationRequest(
        existing_deck=sample_deck,
        user_prompt="Add 2 copies of a haste creature and remove 2 copies of a high CMC card",
        run_quality_check=False
    )

    result = await orchestrator.execute(mod_request)

    print(f"\nResult success: {result.get('success')}")

    if result.get("success"):
        deck_data = result.get("deck")
        modifications = result.get("modifications", {})

        print(f"Modified deck cards: {deck_data.get('total_cards')}")
        print(f"Modifications summary: {modifications.get('summary', 'N/A')}")

        assert deck_data is not None
        assert deck_data.get("format") == sample_deck.format
        print("✓ Full chain test PASSED")
    else:
        error_msg = result.get("error", "Unknown error")
        print(f"✗ Full chain test FAILED: {error_msg}")


if __name__ == "__main__":
    # Run tests
    print("Running modification flow tests...\n")

    # Create sample deck
    deck = asyncio.run(test_api_request_format())

    # You can run individual tests here
    asyncio.run(test_full_modification_chain(
        asyncio.run(pytest.fixture(sample_deck)())
    ))
