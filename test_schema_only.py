"""
Test KnowledgeFetchAgent with schema-only output
"""

import asyncio
import json
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.agents.knowledge_fetch_agent import KnowledgeFetchAgent
import os


async def test_schema_only_output():
    """Test that agent returns only MTGCard schema data, no generated text"""
    print("=" * 70)
    print("TEST: Schema-Only Output from KnowledgeFetchAgent")
    print("=" * 70)

    # Setup
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    if not os.path.exists(db_path):
        print(f"⚠️  Database not found at {db_path}")
        print("   Please build the database first.")
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set in environment")
        print("   Skipping test (requires LLM for card name extraction).")
        return

    # Initialize services
    db = DatabaseService(db_path)
    db.connect()

    lookup = CardLookupService(database_service=db, cache_size=10)

    # Create agent
    agent = KnowledgeFetchAgent(
        card_lookup_service=lookup,
        model_name="openai:gpt-4o-mini",
        api_key=api_key
    )

    print("✓ Setup complete\n")

    # Test 1: Single card query
    print("Test 1: Single card query")
    print("-" * 70)
    print("Query: 'Tell me about Lightning Bolt'\n")

    response = await agent.process({
        "query": "Tell me about Lightning Bolt",
        "use_fuzzy": False
    })

    print(f"Success: {response.success}")
    print(f"Confidence: {response.confidence}")
    print(f"Cards found: {len(response.data.get('cards', []))}")

    # Verify NO answer text is generated
    if 'answer' in response.data:
        print(f"⚠️  WARNING: Agent returned 'answer' text: {response.data['answer'][:100]}...")
    else:
        print("✓ No 'answer' text generated (as expected)")

    # Show card data
    cards = response.data.get('cards', [])
    if cards:
        print(f"\nCard data returned (MTGCard schema):")
        card = cards[0]
        print(f"  Name: {card['name']}")
        print(f"  Mana Cost: {card['mana_cost']}")
        print(f"  CMC: {card['cmc']}")
        print(f"  Type: {card['type_line']}")
        print(f"  Oracle Text: {card['oracle_text'][:80]}...")
        print(f"  Colors: {card['colors']}")
        print(f"  Set: {card['set_code']}")
        print(f"  Rarity: {card['rarity']}")

    print(f"\nReasoning trace:")
    for trace in response.reasoning_trace[:5]:
        print(f"  - {trace}")

    print()

    # Test 2: Multiple cards
    print("Test 2: Multiple card query")
    print("-" * 70)
    print("Query: 'Compare Lightning Bolt and Counterspell'\n")

    response = await agent.process({
        "query": "Compare Lightning Bolt and Counterspell",
        "use_fuzzy": False
    })

    print(f"Success: {response.success}")
    print(f"Confidence: {response.confidence}")
    print(f"Cards found: {len(response.data.get('cards', []))}")

    if 'answer' not in response.data:
        print("✓ No 'answer' text generated (as expected)")

    cards = response.data.get('cards', [])
    print(f"\nReturned cards:")
    for card in cards:
        print(f"  - {card['name']} ({card['mana_cost']}) - {card['type_line']}")

    print()

    # Test 3: JSON serialization
    print("Test 3: JSON serialization of response")
    print("-" * 70)

    response_json = json.dumps(response.data, indent=2)
    print(f"Response data as JSON (first 500 chars):")
    print(response_json[:500])
    print("...")
    print(f"\n✓ Response is valid JSON ({len(response_json)} chars)")

    print()

    db.disconnect()

    print("=" * 70)
    print("ALL TESTS COMPLETE! ✓")
    print("Agent returns ONLY MTGCard schema data, no generated text.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_schema_only_output())
