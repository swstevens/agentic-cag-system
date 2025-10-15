"""
Test Comprehensive Deck Analyzer
"""

import asyncio
from mtg_cag_system.services.database_service import DatabaseService
from mtg_cag_system.services.card_lookup_service import CardLookupService
from mtg_cag_system.services.deck_analyzer import DeckAnalyzer

def test_deck_analysis():
    print("=" * 80)
    print("COMPREHENSIVE DECK ANALYSIS TEST")
    print("=" * 80)
    print()
    
    # Setup
    db = DatabaseService("./mtg_cag_system/data/cards.db")
    db.connect()
    card_lookup = CardLookupService(database_service=db, cache_size=200)
    
    # Build the same deck
    deck_plan = [
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
    
    deck = []
    for card_name, count in deck_plan:
        card = card_lookup.get_card(card_name)
        if card:
            for _ in range(count):
                deck.append(card.model_dump())
    
    print(f"Analyzing deck with {len(deck)} cards...\n")
    
    # Analyze deck
    analysis = DeckAnalyzer.analyze_full_deck(deck, archetype='aggro')
    
    # Display results
    print("=" * 80)
    print("MANA CURVE ANALYSIS")
    print("=" * 80)
    curve = analysis['mana_curve']
    print(f"Average CMC: {curve['average_cmc']}")
    print(f"Ideal range for aggro: {curve['ideal_range']}")
    print(f"Quality: {curve['curve_quality']}")
    print(f"\nCurve distribution:")
    for cmc, count in curve['curve'].items():
        if count > 0:
            bar = "█" * (count // 2)
            print(f"  CMC {cmc}: {count:2d} cards {bar}")
    print(f"\nFocus percentage (CMC {curve['focus_cmcs']}): {curve['focus_percentage']}%")
    print()
    
    print("=" * 80)
    print("LAND RATIO ANALYSIS")
    print("=" * 80)
    land = analysis['land_ratio']
    print(f"Lands: {land['land_count']} ({land['land_percentage']}%)")
    print(f"Non-lands: {land['nonland_count']}")
    print(f"Ideal range for aggro: {land['ideal_percentage'][0]:.0f}%-{land['ideal_percentage'][1]:.0f}%")
    print(f"Quality: {land['ratio_quality']}")
    print()
    
    print("=" * 80)
    print("COLOR DISTRIBUTION")
    print("=" * 80)
    colors = analysis['color_distribution']
    print(f"Color identity: {colors['color_identity']}")
    print(f"Number of colors: {colors['num_colors']}")
    print(f"Monocolor: {colors['is_monocolor']}")
    if colors['color_counts']:
        print(f"\nColor breakdown:")
        for color, count in colors['color_counts'].items():
            pct = colors['color_distribution'][color]
            print(f"  {color}: {count} cards ({pct}%)")
    print()
    
    print("=" * 80)
    print("CARD TYPE DISTRIBUTION")
    print("=" * 80)
    types = analysis['card_types']
    for card_type, count in types['type_counts'].items():
        pct = types['type_percentages'][card_type]
        print(f"  {card_type}: {count} cards ({pct}%)")
    print()
    
    print("=" * 80)
    print("COMBOS & SYNERGIES")
    print("=" * 80)
    combos = analysis['combos']
    print(f"Combos detected: {combos['total_combos']}")
    for combo in combos['combos']:
        print(f"  ✓ {combo['name']}")
        print(f"    Cards: {', '.join(combo['cards'])}")
        print(f"    Effect: {combo['description']}")
    
    print(f"\nSynergies detected: {combos['total_synergies']}")
    for synergy in combos['synergies']:
        print(f"  • {synergy}")
    print()
    
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    if analysis['recommendations']:
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"{i}. {rec}")
    else:
        print("✓ Deck construction looks good!")
    print()
    
    print("=" * 80)
    print(f"OVERALL SCORE: {analysis['overall_score']:.1f}/100")
    print("=" * 80)
    
    db.disconnect()

if __name__ == "__main__":
    test_deck_analysis()
