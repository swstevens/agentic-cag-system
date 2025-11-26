"""
Deck Improvement Test

Takes a poorly constructed deck, analyzes it, and automatically improves it
based on the analysis recommendations.
"""

import asyncio
import os
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer
from mtg_cag_system.agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from collections import Counter


async def improve_deck(original_decklist, deck_name, archetype, format_name="Modern"):
    """
    Analyze a deck and automatically improve it based on recommendations

    Args:
        original_decklist: List of (card_name, count) tuples
        deck_name: Name of the deck
        archetype: Deck archetype
        format_name: Format to build for

    Returns:
        Improved decklist
    """
    print("=" * 80)
    print(f"DECK IMPROVEMENT: {deck_name}")
    print("=" * 80)
    print()

    # Setup
    db_path = "../mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./mtg_cag_system/data/cards.db"

    db = DatabaseService(db_path)
    db.connect()
    card_lookup = CardLookupService(database_service=db, cache_size=200)

    api_key = os.getenv("OPENAI_API_KEY")
    symbolic_agent = SymbolicReasoningAgent(
        model_name="openai:gpt-4o-mini",
        api_key=api_key
    )

    # =========================================================================
    # STEP 1: Analyze Original Deck
    # =========================================================================
    print("STEP 1: ANALYZING ORIGINAL DECK")
    print("-" * 80)

    original_deck = []
    for card_name, count in original_decklist:
        card = card_lookup.get_card(card_name)
        if card:
            for _ in range(count):
                original_deck.append(card.model_dump())

    print(f"Original deck size: {len(original_deck)} cards")

    # Analyze
    original_analysis = DeckAnalyzer.analyze_full_deck(original_deck, archetype=archetype)
    original_score = original_analysis['overall_score']

    print(f"Original score: {original_score:.1f}/100")
    print(f"\nIssues found:")

    issues = []

    # Check mana curve
    curve = original_analysis['mana_curve']
    if curve['curve_quality'] != 'good':
        issues.append(f"Mana curve: avg CMC {curve['average_cmc']} (ideal: {curve['ideal_range']})")
        print(f"  ⚠️  Mana curve: {curve['curve_quality']}")

    # Check land ratio
    land = original_analysis['land_ratio']
    if land['ratio_quality'] != 'good':
        issues.append(f"Land ratio: {land['land_percentage']}% (ideal: {land['ideal_percentage'][0]:.0f}%-{land['ideal_percentage'][1]:.0f}%)")
        print(f"  ⚠️  Land ratio: {land['ratio_quality']}")

    # Check card count
    if len(original_deck) < 60:
        issues.append(f"Only {len(original_deck)} cards (need 60)")
        print(f"  ⚠️  Card count: {len(original_deck)}/60")
    elif len(original_deck) > 60:
        issues.append(f"Too many cards: {len(original_deck)} (max 60)")
        print(f"  ⚠️  Card count: {len(original_deck)}/60")

    print()

    if not issues:
        print("✅ Deck looks good! No improvements needed.")
        db.disconnect()
        return original_decklist

    # =========================================================================
    # STEP 2: Generate Improvements
    # =========================================================================
    print("STEP 2: GENERATING IMPROVEMENTS")
    print("-" * 80)
    print()

    # Convert deck to card counts
    card_counts = Counter()
    for card in original_deck:
        card_counts[card['name']] += 1

    improved_list = dict(card_counts)

    # Fix 1: Adjust card count to 60
    current_size = sum(improved_list.values())
    if current_size < 60:
        cards_to_add = 60 - current_size
        print(f"📝 Need to add {cards_to_add} cards to reach 60")

        # Add more lands if land ratio is low
        if land['ratio_quality'] == 'too_few_lands':
            land_name = "Mountain"  # Default for red
            if land_name in improved_list:
                improved_list[land_name] += cards_to_add
            else:
                improved_list[land_name] = cards_to_add
            print(f"   → Adding {cards_to_add}x {land_name}")
        else:
            # Add more of existing good cards (prioritize low CMC)
            low_cmc_cards = [(name, count) for name, count in improved_list.items()
                           if 'Land' not in name and count < 4]
            if low_cmc_cards:
                # Add to first low-count card
                card_to_boost = low_cmc_cards[0][0]
                add_count = min(cards_to_add, 4 - low_cmc_cards[0][1])
                improved_list[card_to_boost] += add_count
                print(f"   → Adding {add_count}x {card_to_boost}")

                if cards_to_add > add_count:
                    # Add lands for the rest
                    land_name = "Mountain"
                    if land_name in improved_list:
                        improved_list[land_name] += (cards_to_add - add_count)
                    else:
                        improved_list[land_name] = (cards_to_add - add_count)
                    print(f"   → Adding {cards_to_add - add_count}x {land_name}")

    elif current_size > 60:
        cards_to_remove = current_size - 60
        print(f"📝 Need to remove {cards_to_remove} cards to reach 60")

        # Remove highest CMC cards first
        deck_with_cmc = []
        for card in original_deck:
            deck_with_cmc.append((card['name'], card.get('cmc', 0)))

        # Sort by CMC (highest first)
        deck_with_cmc.sort(key=lambda x: x[1], reverse=True)

        removed = 0
        for card_name, cmc in deck_with_cmc:
            if removed >= cards_to_remove:
                break
            if improved_list[card_name] > 0:
                improved_list[card_name] -= 1
                removed += 1
                print(f"   → Removing 1x {card_name} (CMC {cmc})")

    # Fix 2: Adjust land count
    current_lands = sum(count for name, count in improved_list.items() if 'Mountain' in name or 'Island' in name or 'Plains' in name or 'Swamp' in name or 'Forest' in name)
    current_nonlands = sum(improved_list.values()) - current_lands

    if land['ratio_quality'] == 'too_few_lands':
        target_lands = int(60 * sum(land['ideal_range']) / 2)
        lands_to_add = target_lands - current_lands

        if lands_to_add > 0:
            print(f"\n📝 Adjusting land count: {current_lands} → {target_lands}")

            # Remove some expensive spells to make room
            removed = 0
            for card in sorted(original_deck, key=lambda x: x.get('cmc', 0), reverse=True):
                if removed >= lands_to_add:
                    break
                if 'Land' not in card['type_line'] and improved_list.get(card['name'], 0) > 2:
                    improved_list[card['name']] -= 1
                    removed += 1
                    print(f"   → Removing 1x {card['name']} (CMC {card.get('cmc', 0)})")

            # Add lands
            land_name = "Mountain"
            if land_name in improved_list:
                improved_list[land_name] += lands_to_add
            else:
                improved_list[land_name] = lands_to_add
            print(f"   → Adding {lands_to_add}x {land_name}")

    elif land['ratio_quality'] == 'too_many_lands':
        target_lands = int(60 * sum(land['ideal_range']) / 2)
        lands_to_remove = current_lands - target_lands

        if lands_to_remove > 0:
            print(f"\n📝 Adjusting land count: {current_lands} → {target_lands}")

            # Remove lands
            land_name = "Mountain"
            if land_name in improved_list:
                remove_count = min(lands_to_remove, improved_list[land_name])
                improved_list[land_name] -= remove_count
                print(f"   → Removing {remove_count}x {land_name}")

            # Add more spells
            # Find good low-CMC cards to add
            good_cards = ["Lightning Bolt", "Lava Spike", "Monastery Swiftspear"]
            for card_name in good_cards:
                if lands_to_remove <= 0:
                    break
                if card_name in improved_list and improved_list[card_name] < 4:
                    add_count = min(lands_to_remove, 4 - improved_list[card_name])
                    improved_list[card_name] += add_count
                    lands_to_remove -= add_count
                    print(f"   → Adding {add_count}x {card_name}")

    # Fix 3: Remove cards that don't fit archetype
    if curve['curve_quality'] == 'too_high' and archetype == 'aggro':
        print(f"\n📝 Removing high-CMC cards for aggro deck")

        # Remove cards with CMC > 4
        for card in original_deck:
            if card.get('cmc', 0) > 4 and improved_list.get(card['name'], 0) > 0:
                remove_count = improved_list[card['name']]
                improved_list[card['name']] = 0
                print(f"   → Removing {remove_count}x {card['name']} (CMC {card.get('cmc', 0)})")

        # Add better aggro cards
        aggressive_cards = [
            ("Goblin Guide", 4),
            ("Monastery Swiftspear", 4),
            ("Lightning Bolt", 4),
            ("Lava Spike", 4),
        ]

        print(f"\n   Adding aggro-appropriate cards:")
        for card_name, target_count in aggressive_cards:
            current_count = improved_list.get(card_name, 0)
            if current_count < target_count:
                add_count = target_count - current_count
                improved_list[card_name] = target_count
                print(f"   → Adding {add_count}x {card_name} (total: {target_count})")

    # Clean up zero-count cards
    improved_list = {name: count for name, count in improved_list.items() if count > 0}

    print()

    # =========================================================================
    # STEP 3: Validate Improved Deck
    # =========================================================================
    print("STEP 3: VALIDATING IMPROVED DECK")
    print("-" * 80)

    # Build improved deck
    improved_deck = []
    for card_name, count in improved_list.items():
        card = card_lookup.get_card(card_name)
        if card:
            for _ in range(count):
                improved_deck.append(card.model_dump())

    # Analyze improved deck
    improved_analysis = DeckAnalyzer.analyze_full_deck(improved_deck, archetype=archetype)
    improved_score = improved_analysis['overall_score']

    print(f"Improved deck size: {len(improved_deck)} cards")
    print(f"Improved score: {improved_score:.1f}/100 (was {original_score:.1f}/100)")
    print(f"Improvement: +{improved_score - original_score:.1f} points")
    print()

    # Validate legality
    validation_response = await symbolic_agent.process({
        'type': 'deck_validation',
        'data': {
            'cards': improved_deck,
            'format': format_name
        }
    })

    val = validation_response.data
    print(f"Legal for {format_name}: {val['valid']}")
    print()

    # =========================================================================
    # STEP 4: Show Improvements
    # =========================================================================
    print("STEP 4: COMPARISON")
    print("-" * 80)
    print()

    print("ORIGINAL DECK:")
    print("-" * 40)
    for card_name, count in sorted(original_decklist, key=lambda x: x[1], reverse=True):
        print(f"  {count}x {card_name}")
    print()

    print("IMPROVED DECK:")
    print("-" * 40)
    for card_name, count in sorted(improved_list.items(), key=lambda x: x[1], reverse=True):
        print(f"  {count}x {card_name}")
    print()

    print("CHANGES MADE:")
    print("-" * 40)

    # Calculate differences
    original_counts = {name: count for name, count in original_decklist}

    changes_made = False
    for card_name in set(list(original_counts.keys()) + list(improved_list.keys())):
        original_count = original_counts.get(card_name, 0)
        improved_count = improved_list.get(card_name, 0)

        if original_count != improved_count:
            changes_made = True
            diff = improved_count - original_count
            if diff > 0:
                print(f"  +{diff}x {card_name}")
            else:
                print(f"  {diff}x {card_name}")

    if not changes_made:
        print("  No changes made")

    print()

    # =========================================================================
    # STEP 5: Show Analysis Comparison
    # =========================================================================
    print("STEP 5: ANALYSIS COMPARISON")
    print("-" * 80)
    print()

    print(f"Mana Curve:")
    print(f"  Original: {original_analysis['mana_curve']['average_cmc']} avg CMC ({original_analysis['mana_curve']['curve_quality']})")
    print(f"  Improved: {improved_analysis['mana_curve']['average_cmc']} avg CMC ({improved_analysis['mana_curve']['curve_quality']})")
    print()

    print(f"Land Ratio:")
    print(f"  Original: {original_analysis['land_ratio']['land_percentage']}% ({original_analysis['land_ratio']['ratio_quality']})")
    print(f"  Improved: {improved_analysis['land_ratio']['land_percentage']}% ({improved_analysis['land_ratio']['ratio_quality']})")
    print()

    print(f"Overall Score:")
    print(f"  Original: {original_score:.1f}/100")
    print(f"  Improved: {improved_score:.1f}/100")

    if improved_score > original_score:
        print(f"  ✅ Improvement: +{improved_score - original_score:.1f} points")
    elif improved_score == original_score:
        print(f"  = No change")
    else:
        print(f"  ⚠️  Worse: {improved_score - original_score:.1f} points")

    print()

    db.disconnect()

    # Return improved decklist
    return [(name, count) for name, count in improved_list.items()]


async def main():
    """Test deck improvement on a bad deck"""

    print("=" * 80)
    print("AUTOMATIC DECK IMPROVEMENT TEST")
    print("=" * 80)
    print()

    # Bad deck that needs improvement
    bad_deck = [
        # Too many expensive creatures
        ("Shivan Dragon", 4),       # 6 CMC
        ("Colossal Dreadmaw", 4),   # 6 CMC
        ("Lava Axe", 4),            # 5 CMC

        # Some good cards (but not enough)
        ("Lightning Bolt", 2),
        ("Goblin Guide", 2),
        ("Monastery Swiftspear", 2),

        # Way too few lands
        ("Mountain", 10),

        # Cards that don't fit aggro
        ("Negate", 4),              # Control card
        ("Cancel", 2),              # Control card
        ("Divination", 3),          # Card draw
    ]

    improved_deck = await improve_deck(
        bad_deck,
        "Poorly Built Red Deck",
        "aggro",
        "Modern"
    )

    print("=" * 80)
    print("IMPROVEMENT COMPLETE!")
    print("=" * 80)
    print()
    print("You can now use the improved decklist:")
    print()
    for card_name, count in sorted(improved_deck, key=lambda x: x[1], reverse=True):
        print(f"  {count}x {card_name}")


if __name__ == "__main__":
    asyncio.run(main())
