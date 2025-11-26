"""
Test Iterative Deck Builder

Tests the complete iterative deck building system that refines
a deck until all validation requirements are satisfied.
"""

import asyncio
import os
import json
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.agents.knowledge_fetch_agent import KnowledgeFetchAgent
from mtg_cag_system.agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from mtg_cag_system.services.deck_builder_service import DeckBuilderService


async def test_iterative_deck_builder():
    """Test full iterative deck building"""

    print("=" * 80)
    print("TEST: Iterative Deck Builder - Build Complete Legal Deck")
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

    # Initialize services
    print("Initializing system...")
    db = DatabaseService(db_path)
    db.connect()

    card_lookup = CardLookupService(database_service=db, cache_size=200)

    model_name = "openai:gpt-4o-mini"

    knowledge_agent = KnowledgeFetchAgent(
        card_lookup_service=card_lookup,
        model_name=model_name,
        api_key=api_key
    )

    symbolic_agent = SymbolicReasoningAgent(
        model_name=model_name,
        api_key=api_key
    )

    # Create deck builder
    deck_builder = DeckBuilderService(
        knowledge_agent=knowledge_agent,
        symbolic_agent=symbolic_agent,
        card_lookup=card_lookup,
        max_iterations=10
    )

    print("✓ System initialized\n")

    # =========================================================================
    # TEST: Build a mono-red aggro deck
    # =========================================================================

    requirements = {
        'colors': ['R'],
        'format': 'Modern',  # Using Modern because more cards are legal
        'archetype': 'aggro',
        'deck_size': 60
    }

    print(f"Building deck with requirements:")
    print(f"  Colors: {requirements['colors']}")
    print(f"  Format: {requirements['format']}")
    print(f"  Archetype: {requirements['archetype']}")
    print(f"  Target size: {requirements['deck_size']}")

    # Build the deck iteratively
    result = await deck_builder.build_deck(requirements)

    # =========================================================================
    # Display Results
    # =========================================================================

    print("\n" + "=" * 80)
    print("DECK BUILD COMPLETE")
    print("=" * 80)
    print()

    print(f"Total Iterations: {result['total_iterations']}")
    print(f"Final Deck Size: {result['deck_size']}")
    print(f"Valid: {result['valid']}")
    print()

    print("Validation Results:")
    print(f"  Card Count Valid: {result['validation']['validations']['card_count']}")
    print(f"  Max Copies Valid: {result['validation']['validations']['max_copies']}")
    print(f"  Format Legal: {result['validation']['validations']['format_legal']}")
    print()

    # =========================================================================
    # Show Deck List
    # =========================================================================

    print("=" * 80)
    print("FINAL DECK LIST")
    print("=" * 80)
    print()

    # Count cards
    card_counts = {}
    for card in result['deck']:
        name = card['name']
        card_counts[name] = card_counts.get(name, 0) + 1

    # Display by card type
    creatures = []
    spells = []
    lands = []

    for name, count in sorted(card_counts.items()):
        # Get one copy to check type
        card = next(c for c in result['deck'] if c['name'] == name)
        type_line = card['type_line']

        entry = f"{count}x {name} ({card['mana_cost'] or 'N/A'})"

        if 'Creature' in type_line:
            creatures.append(entry)
        elif 'Land' in type_line:
            lands.append(entry)
        else:
            spells.append(entry)

    print(f"CREATURES ({len(creatures)} types):")
    for creature in creatures:
        print(f"  {creature}")

    print(f"\nSPELLS ({len(spells)} types):")
    for spell in spells:
        print(f"  {spell}")

    print(f"\nLANDS ({len(lands)} types):")
    for land in lands:
        print(f"  {land}")

    print(f"\nTOTAL: {result['deck_size']} cards")
    print()

    # =========================================================================
    # Show Iteration History
    # =========================================================================

    print("=" * 80)
    print("BUILD HISTORY")
    print("=" * 80)
    print()

    for iteration_data in result['iterations']:
        print(f"Iteration {iteration_data['iteration']}:")
        print(f"  Deck size: {iteration_data['deck_size']}")
        print(f"  Cards added: {iteration_data['cards_added']}")

        if iteration_data['validation']:
            val = iteration_data['validation']
            print(f"  Validation: {val['valid']} - {val['validations']}")
        print()

    # =========================================================================
    # Export deck to file
    # =========================================================================

    print("=" * 80)
    print("EXPORTING DECK")
    print("=" * 80)
    print()

    # Export as JSON
    deck_export = {
        'format': requirements['format'],
        'archetype': requirements['archetype'],
        'colors': requirements['colors'],
        'mainboard': []
    }

    for name, count in sorted(card_counts.items()):
        card = next(c for c in result['deck'] if c['name'] == name)
        deck_export['mainboard'].append({
            'count': count,
            'name': name,
            'mana_cost': card['mana_cost'],
            'type': card['type_line']
        })

    filename = "mono_red_aggro_deck.json"
    with open(filename, 'w') as f:
        json.dump(deck_export, f, indent=2)

    print(f"✓ Deck exported to {filename}")
    print()

    # =========================================================================
    # Cleanup
    # =========================================================================

    db.disconnect()

    print("=" * 80)
    print("TEST COMPLETE! ✓")
    print("=" * 80)

    # Return result for verification
    return result


if __name__ == "__main__":
    result = asyncio.run(test_iterative_deck_builder())

    # Final verification
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    if result['valid']:
        print("✅ DECK IS COMPLETE AND LEGAL!")
        print(f"   Built in {result['total_iterations']} iterations")
        print(f"   {result['deck_size']} cards ready to play!")
    else:
        print("⚠️  Deck built but may have issues:")
        print(f"   {result['validation']}")
