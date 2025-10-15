"""
Full System Integration Test: Build a Mono-Red Aggro Deck

Tests the complete multi-agent system:
- SchedulingAgent: Creates a plan for deck building
- KnowledgeFetchAgent: Retrieves red aggressive cards
- SymbolicReasoningAgent: Validates deck construction
- AgentOrchestrator: Coordinates all agents

Goal: Build a 60-card mono-red aggro deck for Standard format
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
from mtg_cag_system.models.query import UserQuery, QueryIntent


async def test_full_system_mono_red_aggro():
    """Full system test: Build a mono-red aggro deck"""

    print("=" * 80)
    print("FULL SYSTEM TEST: Build Mono-Red Aggro Deck for Standard")
    print("=" * 80)
    print()

    # Check prerequisites
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("   Please build the database first.")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set in environment")
        return

    # =========================================================================
    # STEP 1: Initialize All Services
    # =========================================================================
    print("Step 1: Initializing System Components")
    print("-" * 80)

    # Database
    db = DatabaseService(db_path)
    db.connect()
    print(f"✓ Database connected ({db.card_count():,} cards)")

    # Card lookup service (replaces old KnowledgeService)
    card_lookup = CardLookupService(database_service=db, cache_size=200)
    print(f"✓ Card lookup service initialized")

    # Multi-tier cache (for orchestrator)
    cache = MultiTierCache()
    print(f"✓ Multi-tier cache initialized")

    # Agents
    model_name = "openai:gpt-4o-mini"

    scheduling_agent = SchedulingAgent(
        model_name=model_name,
        api_key=api_key
    )
    print(f"✓ Scheduling agent initialized")

    knowledge_agent = KnowledgeFetchAgent(
        card_lookup_service=card_lookup,
        model_name=model_name,
        api_key=api_key
    )
    print(f"✓ Knowledge fetch agent initialized")

    symbolic_agent = SymbolicReasoningAgent(
        model_name=model_name,
        api_key=api_key
    )
    print(f"✓ Symbolic reasoning agent initialized")

    # Orchestrator
    orchestrator = AgentOrchestrator(
        scheduling_agent=scheduling_agent,
        knowledge_agent=knowledge_agent,
        symbolic_agent=symbolic_agent,
        cache=cache
    )
    print(f"✓ Agent orchestrator initialized")
    print()

    # =========================================================================
    # STEP 2: Create User Query
    # =========================================================================
    print("Step 2: Creating User Query")
    print("-" * 80)

    query = UserQuery(
        query_id="test_001",
        session_id="test_session",
        query_text="Build me a mono-red aggro deck for Standard with efficient burn spells and aggressive creatures",
        intent=QueryIntent(
            primary_intent="deck_building",
            requires_card_lookup=True,
            requires_symbolic_reasoning=True,
            format_constraint="Standard"
        ),
        context={
            "format": "Standard",
            "deck_archetype": "aggro",
            "colors": ["R"],
            "strategy": "aggressive creatures and burn spells"
        }
    )

    print(f"Query: {query.query_text}")
    print(f"Format: {query.context.get('format')}")
    print(f"Archetype: {query.context.get('deck_archetype')}")
    print(f"Colors: {query.context.get('colors')}")
    print()

    # =========================================================================
    # STEP 3: Process Query Through Orchestrator
    # =========================================================================
    print("Step 3: Processing Query Through Multi-Agent System")
    print("-" * 80)
    print()

    response = await orchestrator.process_query(query)

    print("RESPONSE RECEIVED")
    print("=" * 80)
    print(f"Query ID: {response.query_id}")
    print(f"Confidence: {response.confidence:.2f}")
    print(f"Sources: {len(response.sources)}")
    print()

    # =========================================================================
    # STEP 4: Examine Agent Contributions
    # =========================================================================
    print("Step 4: Agent Contributions")
    print("-" * 80)
    print()

    # Scheduling Agent
    if "scheduling" in response.agent_contributions:
        sched_response = response.agent_contributions["scheduling"]
        print(f"📅 SCHEDULING AGENT (Confidence: {sched_response.confidence})")
        print(f"   Plan created with {len(sched_response.data.get('plan', []))} steps")
        for step in sched_response.data.get('plan', [])[:3]:
            print(f"   - Step {step.get('step_number')}: {step.get('action')[:60]}...")
        print()

    # Knowledge Fetch Agent
    if "knowledge" in response.agent_contributions:
        knowledge_response = response.agent_contributions["knowledge"]
        print(f"📚 KNOWLEDGE FETCH AGENT (Confidence: {knowledge_response.confidence})")
        cards = knowledge_response.data.get('cards', [])
        print(f"   Found {len(cards)} cards")

        # Show first few cards
        for i, card in enumerate(cards[:5]):
            print(f"   {i+1}. {card['name']} ({card['mana_cost']}) - {card['type_line']}")

        if len(cards) > 5:
            print(f"   ... and {len(cards) - 5} more cards")

        # Show lookup stats
        lookup_stats = knowledge_response.data.get('lookup_stats', {})
        print(f"   Lookup Stats: {lookup_stats.get('tier1_hits')} cache hits, "
              f"{lookup_stats.get('tier2_hits')} database hits")
        print()

    # Symbolic Reasoning Agent
    if "symbolic" in response.agent_contributions:
        symbolic_response = response.agent_contributions["symbolic"]
        print(f"🧮 SYMBOLIC REASONING AGENT (Confidence: {symbolic_response.confidence})")
        print(f"   Validation: {symbolic_response.data}")
        print()

    # =========================================================================
    # STEP 5: Show Reasoning Chain
    # =========================================================================
    print("Step 5: Reasoning Chain")
    print("-" * 80)

    for i, step in enumerate(response.reasoning_chain, 1):
        print(f"{i}. [{step['agent_type']}] {step['action']} (confidence: {step['confidence']})")
    print()

    # =========================================================================
    # STEP 6: Final Answer
    # =========================================================================
    print("Step 6: Final Answer")
    print("-" * 80)
    print(response.answer)
    print()

    # =========================================================================
    # STEP 7: Export Results as JSON
    # =========================================================================
    print("Step 7: Exporting Results")
    print("-" * 80)

    result_data = {
        "query": query.query_text,
        "confidence": response.confidence,
        "cards_found": len(response.agent_contributions.get("knowledge", {}).data.get("cards", [])),
        "sources": response.sources,
        "reasoning_steps": len(response.reasoning_chain),
        "metadata": response.metadata
    }

    print(json.dumps(result_data, indent=2))
    print()

    # =========================================================================
    # STEP 8: Cleanup
    # =========================================================================
    print("Step 8: Cleanup")
    print("-" * 80)

    db.disconnect()
    print("✓ Database disconnected")
    print()

    print("=" * 80)
    print("FULL SYSTEM TEST COMPLETE! ✓")
    print("=" * 80)


async def test_simple_card_query():
    """Simpler test: Just fetch some red aggro cards"""

    print("\n" + "=" * 80)
    print("SIMPLE TEST: Fetch Red Aggro Cards")
    print("=" * 80)
    print()

    # Setup
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    if not os.path.exists(db_path):
        print("❌ Database not found")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ API key not set")
        return

    db = DatabaseService(db_path)
    db.connect()

    card_lookup = CardLookupService(database_service=db, cache_size=50)

    # Search for red aggro cards directly in database
    print("Searching database for red aggro cards...")
    print()

    # Try to find some classic red aggro cards
    test_cards = ["Lightning Bolt", "Monastery Swiftspear", "Goblin Guide",
                  "Eidolon of the Great Revel", "Lava Spike"]

    found_cards = []
    for card_name in test_cards:
        card = card_lookup.get_card(card_name)
        if card:
            found_cards.append(card)
            print(f"✓ {card.name} ({card.mana_cost}) - {card.oracle_text[:50]}...")

    print(f"\nFound {len(found_cards)}/{len(test_cards)} cards")

    # Test with Knowledge Agent
    print("\n" + "-" * 80)
    print("Testing Knowledge Agent extraction...")
    print()

    knowledge_agent = KnowledgeFetchAgent(
        card_lookup_service=card_lookup,
        model_name="openai:gpt-4o-mini",
        api_key=api_key
    )

    response = await knowledge_agent.process({
        "query": "Show me Lightning Bolt and Goblin Guide",
        "use_fuzzy": True
    })

    print(f"Agent found {len(response.data.get('cards', []))} cards:")
    for card in response.data.get('cards', []):
        print(f"  - {card['name']} ({card['mana_cost']})")

    print()
    db.disconnect()


if __name__ == "__main__":
    # Run both tests
    asyncio.run(test_simple_card_query())
    asyncio.run(test_full_system_mono_red_aggro())
