"""
Full System Integration Test v2: Build Deck with Specific Cards

This version provides explicit card names to test the full pipeline.
"""

import asyncio
import os
import json
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.services.cache_service import MultiTierCache
from mtg_cag_system.agents.scheduling_agent import SchedulingAgent
from mtg_cag_system.agents.knowledge_fetch_agent import KnowledgeFetchAgent
from mtg_cag_system.agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from mtg_cag_system.controllers.orchestrator import AgentOrchestrator
from mtg_cag_system.models.query import UserQuery, QueryIntent, QueryType


async def test_with_specific_cards():
    """Test with explicit card names"""

    print("=" * 80)
    print("FULL SYSTEM TEST: Fetch and Validate Specific Cards for Red Aggro")
    print("=" * 80)
    print()

    # Setup
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    if not os.path.exists(db_path):
        print(f"❌ Database not found")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ API key not set")
        return

    print("Initializing system...")
    db = DatabaseService(db_path)
    db.connect()

    card_lookup = CardLookupService(database_service=db, cache_size=200)
    cache = MultiTierCache()
    model_name = "openai:gpt-4o-mini"

    scheduling_agent = SchedulingAgent(model_name=model_name, api_key=api_key)
    knowledge_agent = KnowledgeFetchAgent(
        card_lookup_service=card_lookup,
        model_name=model_name,
        api_key=api_key
    )
    symbolic_agent = SymbolicReasoningAgent(model_name=model_name, api_key=api_key)

    orchestrator = AgentOrchestrator(
        scheduling_agent=scheduling_agent,
        knowledge_agent=knowledge_agent,
        symbolic_agent=symbolic_agent,
        cache=cache
    )

    print("✓ System initialized\n")

    # =========================================================================
    # TEST 1: Query with specific card names
    # =========================================================================
    print("TEST 1: Query with Specific Card Names")
    print("-" * 80)

    query = UserQuery(
        query_id="test_002",
        session_id="test_session",
        query_text="Tell me about Lightning Bolt, Goblin Guide, and Monastery Swiftspear for a red aggro deck",
        intent=QueryIntent(
            primary_intent=QueryType.CARD_SEARCH,
            requires_card_lookup=True,
            requires_symbolic_reasoning=False
        ),
        context={
            "format": "Modern",
            "deck_archetype": "aggro"
        }
    )

    print(f"Query: {query.query_text}\n")

    response = await orchestrator.process_query(query)

    print(f"✓ Response received (confidence: {response.confidence:.2f})")
    print(f"✓ Sources: {response.sources}")
    print()

    # Show cards found
    if "knowledge" in response.agent_contributions:
        knowledge_response = response.agent_contributions["knowledge"]
        cards = knowledge_response.data.get('cards', [])

        print(f"CARDS FOUND: {len(cards)}")
        print("-" * 80)
        for card in cards:
            print(f"\n📋 {card['name']}")
            print(f"   Mana Cost: {card['mana_cost']}")
            print(f"   CMC: {card['cmc']}")
            print(f"   Type: {card['type_line']}")
            print(f"   Text: {card['oracle_text'][:100]}...")
            print(f"   Colors: {card['colors']}")
            print(f"   Rarity: {card['rarity']}")

        # Show lookup performance
        lookup_stats = knowledge_response.data.get('lookup_stats', {})
        print(f"\nLOOKUP PERFORMANCE:")
        print(f"  Tier 1 (cache) hits: {lookup_stats.get('tier1_hits')}")
        print(f"  Tier 2 (database) hits: {lookup_stats.get('tier2_hits')}")
        print(f"  Miss rate: {lookup_stats.get('total_misses')}")
        print(f"  Overall hit rate: {lookup_stats.get('overall_hit_rate')}")

    print()

    # =========================================================================
    # TEST 2: Build a simple deck and validate
    # =========================================================================
    print("\nTEST 2: Build and Validate a Simple Deck")
    print("-" * 80)

    # Manually fetch cards to build a deck
    print("Fetching cards for deck construction...")

    deck_card_names = [
        # Creatures (20)
        "Goblin Guide", "Goblin Guide", "Goblin Guide", "Goblin Guide",
        "Monastery Swiftspear", "Monastery Swiftspear", "Monastery Swiftspear", "Monastery Swiftspear",
        "Eidolon of the Great Revel", "Eidolon of the Great Revel", "Eidolon of the Great Revel", "Eidolon of the Great Revel",
        # Burn Spells (20)
        "Lightning Bolt", "Lightning Bolt", "Lightning Bolt", "Lightning Bolt",
        "Lava Spike", "Lava Spike", "Lava Spike", "Lava Spike",
        # Lands (20)
        "Mountain", "Mountain", "Mountain", "Mountain", "Mountain",
        "Mountain", "Mountain", "Mountain", "Mountain", "Mountain",
        "Mountain", "Mountain", "Mountain", "Mountain", "Mountain",
        "Mountain", "Mountain", "Mountain", "Mountain", "Mountain"
    ]

    # Fetch unique cards
    unique_cards = {}
    for card_name in set(deck_card_names):
        card = card_lookup.get_card(card_name)
        if card:
            unique_cards[card_name] = card
            print(f"  ✓ {card_name}")

    print(f"\nFetched {len(unique_cards)} unique cards")

    # Build deck data structure
    deck_cards = []
    for card_name in deck_card_names:
        if card_name in unique_cards:
            deck_cards.append(unique_cards[card_name].dict())

    print(f"Constructed deck with {len(deck_cards)} cards\n")

    # Validate with Symbolic Reasoning Agent
    print("Validating deck with Symbolic Reasoning Agent...")

    validation_input = {
        "type": "deck_validation",
        "data": {
            "cards": deck_cards,
            "format": "Modern"
        }
    }

    validation_response = await symbolic_agent.process(validation_input)

    print(f"\nVALIDATION RESULTS:")
    print(f"  Valid: {validation_response.data.get('valid')}")
    print(f"  Validations:")
    for key, value in validation_response.data.get('validations', {}).items():
        status = "✓" if value else "✗"
        print(f"    {status} {key}: {value}")

    print()

    # =========================================================================
    # TEST 3: Show reasoning chain
    # =========================================================================
    print("\nTEST 3: Reasoning Chain Analysis")
    print("-" * 80)

    print(f"Total reasoning steps: {len(response.reasoning_chain)}")
    for i, step in enumerate(response.reasoning_chain, 1):
        print(f"  {i}. [{step['agent_type']}] {step['action']}")
        print(f"     Confidence: {step['confidence']}")

    print()

    # =========================================================================
    # Cleanup
    # =========================================================================
    db.disconnect()
    print("=" * 80)
    print("ALL TESTS COMPLETE! ✓")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_with_specific_cards())
