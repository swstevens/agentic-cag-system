"""
Manual test script to demonstrate the API modification endpoint.

This script shows how the frontend would interact with the /api/chat endpoint
for both new deck creation and deck modification.
"""

import asyncio
import json
from v3.api import app, ChatRequest, ChatResponse
from v3.models.deck import Deck


async def test_new_deck_creation():
    """Test creating a new deck through the API."""
    print("\n" + "="*60)
    print("TEST 1: New Deck Creation")
    print("="*60)

    request = ChatRequest(
        message="Build a Standard red aggro deck"
    )

    print(f"Request: {request.message}")
    print(f"Has existing_deck: {request.existing_deck is not None}")

    # Simulate API call
    from v3.fsm.orchestrator import FSMOrchestrator
    orchestrator = FSMOrchestrator(db_path="v3/data/cards.db")

    # Parse request (simulating what the API does)
    from v3.api import parse_deck_request
    deck_request = parse_deck_request(request.message, request.context)

    print(f"\nParsed request:")
    print(f"  Format: {deck_request['format']}")
    print(f"  Colors: {deck_request['colors']}")
    print(f"  Archetype: {deck_request['archetype']}")

    # Execute through orchestrator
    result = await orchestrator.execute(deck_request)

    if result["success"]:
        data = result["data"]
        deck_dict = data["deck"]
        quality_metrics = data["quality_metrics"]

        print(f"\n✓ SUCCESS!")
        print(f"  Deck archetype: {deck_dict['archetype']}")
        print(f"  Total cards: {deck_dict['total_cards']}")
        print(f"  Quality score: {quality_metrics['overall_score']:.2f}")
        print(f"  Iterations: {data['iteration_count']}")

        return deck_dict
    else:
        print(f"\n✗ FAILED: {result.get('error')}")
        return None


async def test_deck_modification(existing_deck_data):
    """Test modifying an existing deck through the API."""
    print("\n" + "="*60)
    print("TEST 2: Deck Modification")
    print("="*60)

    if not existing_deck_data:
        print("⚠ No deck provided, skipping modification test")
        return

    request = ChatRequest(
        message="Add more card draw spells",
        existing_deck=existing_deck_data
    )

    print(f"Request: {request.message}")
    print(f"Has existing_deck: {request.existing_deck is not None}")
    print(f"Original deck size: {existing_deck_data['total_cards']} cards")

    # Simulate API call
    from v3.fsm.orchestrator import FSMOrchestrator
    from v3.models.deck import DeckModificationRequest

    orchestrator = FSMOrchestrator(db_path="v3/data/cards.db")

    # Parse existing deck
    deck = Deck.model_validate(request.existing_deck)

    # Create modification request
    mod_request = DeckModificationRequest(
        existing_deck=deck,
        user_prompt=request.message,
        run_quality_check=False
    )

    print(f"\nModification request created:")
    print(f"  User prompt: {mod_request.user_prompt}")
    print(f"  Run quality check: {mod_request.run_quality_check}")

    # Execute through orchestrator
    result = await orchestrator.execute(mod_request)

    if result.get("success"):
        deck_dict = result.get("deck")
        modifications = result.get("modifications", {})

        print(f"\n✓ SUCCESS!")
        print(f"  Modified deck size: {deck_dict.get('total_cards')} cards")
        print(f"  Modifications summary: {modifications.get('summary', 'N/A')}")

        if modifications.get('quality_after'):
            print(f"  Quality score: {modifications['quality_after']:.2f}")

        return deck_dict
    else:
        error_msg = result.get("error", "Unknown error")
        print(f"\n✗ FAILED: {error_msg}")
        return None


async def test_multiple_modifications(deck_data):
    """Test multiple sequential modifications."""
    print("\n" + "="*60)
    print("TEST 3: Sequential Modifications")
    print("="*60)

    if not deck_data:
        print("⚠ No deck provided, skipping sequential test")
        return

    modifications = [
        "Make the deck more aggressive",
        "Add more removal spells",
        "Improve the mana curve"
    ]

    from v3.fsm.orchestrator import FSMOrchestrator
    from v3.models.deck import DeckModificationRequest

    orchestrator = FSMOrchestrator(db_path="v3/data/cards.db")
    current_deck_data = deck_data

    for i, modification in enumerate(modifications, 1):
        print(f"\n--- Modification {i}: {modification} ---")

        deck = Deck.model_validate(current_deck_data)
        mod_request = DeckModificationRequest(
            existing_deck=deck,
            user_prompt=modification,
            run_quality_check=False
        )

        result = await orchestrator.execute(mod_request)

        if result.get("success"):
            current_deck_data = result.get("deck")
            modifications_made = result.get("modifications", {})

            print(f"  ✓ Applied: {modifications_made.get('summary', 'N/A')}")
            print(f"  Deck size: {current_deck_data.get('total_cards')} cards")
        else:
            print(f"  ✗ Failed: {result.get('error')}")
            break

    print(f"\n✓ Sequential modifications complete!")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DECK MODIFICATION API MANUAL TESTS")
    print("="*60)

    # Test 1: Create new deck
    deck_data = await test_new_deck_creation()

    # Test 2: Modify the deck
    if deck_data:
        modified_deck = await test_deck_modification(deck_data)

        # Test 3: Multiple modifications
        if modified_deck:
            await test_multiple_modifications(modified_deck)

    print("\n" + "="*60)
    print("ALL TESTS COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
