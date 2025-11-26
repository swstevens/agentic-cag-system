"""
Deck Review Test

Import an existing decklist and review its quality using our analysis tools.
Tests both a good deck and a poorly constructed deck.
"""

import asyncio
import os
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer
from mtg_cag_system.agents.symbolic_reasoning_agent import SymbolicReasoningAgent


async def review_deck(deck_list, deck_name, archetype, format_name="Modern"):
    """
    Review a deck and provide comprehensive feedback

    Args:
        deck_list: List of (card_name, count) tuples
        deck_name: Name of the deck
        archetype: Deck archetype
        format_name: Format to validate against
    """
    print("=" * 80)
    print(f"DECK REVIEW: {deck_name}")
    print("=" * 80)
    print()

    # Setup
    db_path = "./mtg_cag_system/data/cards.db"
    if not os.path.exists(db_path):
        db_path = "./data/cards.db"

    db = DatabaseService(db_path)
    db.connect()
    card_lookup = CardLookupService(database_service=db, cache_size=200)

    api_key = os.getenv("OPENAI_API_KEY")
    symbolic_agent = SymbolicReasoningAgent(
        model_name="openai:gpt-4o-mini",
        api_key=api_key
    )

    # Build deck from list
    deck = []
    missing_cards = []

    print("Loading decklist...")
    for card_name, count in deck_list:
        card = card_lookup.get_card(card_name)
        if card:
            for _ in range(count):
                deck.append(card.model_dump())
            print(f"  ✓ {count}x {card_name}")
        else:
            missing_cards.append((card_name, count))
            print(f"  ✗ {count}x {card_name} - NOT FOUND")

    total_cards = len(deck)
    print(f"\nLoaded: {total_cards} cards")
    if missing_cards:
        print(f"Missing: {len(missing_cards)} unique cards")
    print()

    # =========================================================================
    # STEP 1: Basic Legality Check
    # =========================================================================
    print("=" * 80)
    print("STEP 1: LEGALITY CHECK")
    print("=" * 80)

    validation_response = await symbolic_agent.process({
        'type': 'deck_validation',
        'data': {
            'cards': deck,
            'format': format_name
        }
    })

    val = validation_response.data
    print(f"\nFormat: {format_name}")
    print(f"Valid: {val['valid']}")
    print("\nValidation Results:")
    for key, value in val['validations'].items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")

    if not val['valid']:
        print("\n⚠️  Deck has legality issues that must be fixed!")
    print()

    # =========================================================================
    # STEP 2: Comprehensive Analysis
    # =========================================================================
    print("=" * 80)
    print("STEP 2: COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    print()

    analysis = DeckAnalyzer.analyze_full_deck(deck, archetype=archetype)

    # Mana Curve
    print("MANA CURVE")
    print("-" * 80)
    curve = analysis['mana_curve']
    print(f"Average CMC: {curve['average_cmc']} (ideal: {curve['ideal_range'][0]}-{curve['ideal_range'][1]})")

    quality_icon = "✅" if curve['curve_quality'] == 'good' else "⚠️"
    print(f"{quality_icon} Quality: {curve['curve_quality']}")

    print("\nDistribution:")
    max_count = max(curve['curve'].values()) if curve['curve'].values() else 1
    for cmc, count in curve['curve'].items():
        if cmc <= 6 or count > 0:  # Show 0-6 and 7+ if populated
            bar_length = int((count / max_count) * 40) if max_count > 0 else 0
            bar = "█" * bar_length
            label = f"{cmc}+" if cmc == 7 else str(cmc)
            print(f"  CMC {label}: {count:2d} {bar}")

    print(f"\nFocus on CMC {curve['focus_cmcs']}: {curve['focus_percentage']}%")
    print()

    # Land Ratio
    print("LAND RATIO")
    print("-" * 80)
    land = analysis['land_ratio']
    print(f"Lands: {land['land_count']} ({land['land_percentage']}%)")
    print(f"Non-lands: {land['nonland_count']}")
    print(f"Ideal: {land['ideal_percentage'][0]:.0f}%-{land['ideal_percentage'][1]:.0f}%")

    quality_icon = "✅" if land['ratio_quality'] == 'good' else "⚠️"
    print(f"{quality_icon} Quality: {land['ratio_quality']}")
    print()

    # Colors
    print("COLOR DISTRIBUTION")
    print("-" * 80)
    colors = analysis['color_distribution']
    print(f"Colors: {colors['color_identity'] if colors['color_identity'] else 'Colorless'}")
    print(f"Number of colors: {colors['num_colors']}")

    if colors['num_colors'] == 1:
        print("✅ Monocolor - consistent mana base")
    elif colors['num_colors'] == 2:
        print("✅ Two-color - should be stable")
    elif colors['num_colors'] >= 3:
        print("⚠️  Multi-color - ensure mana fixing!")

    if colors['color_distribution']:
        print("\nBreakdown:")
        for color, pct in colors['color_distribution'].items():
            print(f"  {color}: {pct}%")
    print()

    # Card Types
    print("CARD TYPES")
    print("-" * 80)
    types = analysis['card_types']
    for card_type, count in sorted(types['type_counts'].items(), key=lambda x: x[1], reverse=True):
        pct = types['type_percentages'][card_type]
        print(f"  {card_type}: {count} ({pct}%)")
    print()

    # Combos & Synergies
    print("COMBOS & SYNERGIES")
    print("-" * 80)
    combos = analysis['combos']

    if combos['combos']:
        print(f"✨ Found {combos['total_combos']} combo(s):")
        for combo in combos['combos']:
            print(f"  • {combo['name']}")
            print(f"    Cards: {', '.join(combo['cards'])}")
            print(f"    Effect: {combo['description']}")
    else:
        print("No known combos detected")

    if combos['synergies']:
        print(f"\n🔗 Found {combos['total_synergies']} synergy pattern(s):")
        for synergy in combos['synergies']:
            print(f"  • {synergy}")
    else:
        print("\nNo major synergies detected")
    print()

    # =========================================================================
    # STEP 3: Recommendations
    # =========================================================================
    print("=" * 80)
    print("STEP 3: RECOMMENDATIONS")
    print("=" * 80)

    if analysis['recommendations']:
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"\n{i}. {rec}")
    else:
        print("\n✅ No issues detected - deck construction looks solid!")
    print()

    # =========================================================================
    # STEP 4: Overall Assessment
    # =========================================================================
    print("=" * 80)
    print("OVERALL ASSESSMENT")
    print("=" * 80)

    score = analysis['overall_score']
    print(f"\n📊 Construction Score: {score:.1f}/100")

    # Grade
    if score >= 90:
        grade = "A"
        assessment = "Excellent"
    elif score >= 80:
        grade = "B"
        assessment = "Good"
    elif score >= 70:
        grade = "C"
        assessment = "Fair"
    elif score >= 60:
        grade = "D"
        assessment = "Poor"
    else:
        grade = "F"
        assessment = "Needs Major Work"

    print(f"Grade: {grade} ({assessment})")

    # Legal status
    if val['valid']:
        print(f"✅ Legal for {format_name} play")
    else:
        print(f"❌ NOT legal for {format_name} play")

    print()

    db.disconnect()
    return analysis, val


async def main():
    """Run deck reviews on multiple decklists"""

    # =========================================================================
    # TEST 1: Well-constructed Modern Burn deck
    # =========================================================================
    good_deck = [
        ("Monastery Swiftspear", 4),
        ("Soul-Scar Mage", 4),
        ("Goblin Guide", 4),
        ("Eidolon of the Great Revel", 4),
        ("Lightning Bolt", 4),
        ("Lava Spike", 4),
        ("Rift Bolt", 4),
        ("Skewer the Critics", 4),
        ("Light Up the Stage", 4),
        ("Mountain", 24)
    ]

    await review_deck(good_deck, "Modern Burn (Good)", "aggro", "Modern")

    print("\n\n")

    # =========================================================================
    # TEST 2: Poorly constructed deck (bad curve, wrong ratios)
    # =========================================================================
    bad_deck = [
        # Too many high CMC creatures
        ("Siege Wurm", 4),          # 7 CMC
        ("Colossal Dreadmaw", 4),   # 6 CMC
        ("Shivan Dragon", 4),       # 6 CMC

        # Random expensive spells
        ("Lava Axe", 4),            # 5 CMC

        # Not enough early game
        ("Lightning Bolt", 2),      # Only 2 copies

        # Way too few lands for high curve
        ("Mountain", 12),           # Only 12 lands!

        # Filler creatures
        ("Goblin Guide", 4),
        ("Soul-Scar Mage", 4),
        ("Eidolon of the Great Revel", 4),

        # Random cards
        ("Shock", 2),
        ("Lava Spike", 2),

        # Wrong archetype cards
        ("Negate", 4),              # Counterspell in aggro?
        ("Divination", 4),          # Card draw at 3 mana?
        ("Cancel", 2)               # More counters?
    ]

    await review_deck(bad_deck, "Poorly Built Red Deck (Bad)", "aggro", "Modern")

    print("\n" + "=" * 80)
    print("DECK REVIEW TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
