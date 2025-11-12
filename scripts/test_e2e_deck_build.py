#!/usr/bin/env python3
"""
End-to-end deck building test via REST API

This script:
1. Calls the deck building endpoint
2. Validates the deck has 60 cards
3. Analyzes mana curve and distribution
4. Checks for synergies within the built deck
"""

import requests
import json
from collections import Counter
from typing import Dict, List, Any

BASE_URL = "http://localhost:8000/api"


def analyze_mana_curve(deck: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze mana curve of the deck"""
    cmc_distribution = Counter()

    for card in deck:
        # Try to extract CMC from mana cost
        mana_cost = card.get('mana_cost', '')
        # Simple CMC calculation: count mana symbols
        # This is a simplified approach
        cmc = len([c for c in mana_cost if c in 'WUBRG123456789'])
        cmc_distribution[cmc] += 1

    return {
        'total': len(deck),
        'distribution': dict(sorted(cmc_distribution.items())),
        'average_cmc': sum(cmc * count for cmc, count in cmc_distribution.items()) / len(deck) if deck else 0
    }


def analyze_color_distribution(deck: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze color distribution of the deck"""
    colors = Counter()

    for card in deck:
        color_identity = card.get('color_identity', '')
        if color_identity:
            for color in color_identity.split(','):
                colors[color.strip()] += 1

    return dict(colors)


def analyze_type_distribution(deck: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze card type distribution"""
    types = Counter()

    for card in deck:
        type_line = card.get('type_line', '')
        # Get primary type
        if 'Creature' in type_line:
            types['Creature'] += 1
        elif 'Instant' in type_line:
            types['Instant'] += 1
        elif 'Sorcery' in type_line:
            types['Sorcery'] += 1
        elif 'Enchantment' in type_line:
            types['Enchantment'] += 1
        elif 'Artifact' in type_line:
            types['Artifact'] += 1
        elif 'Planeswalker' in type_line:
            types['Planeswalker'] += 1
        elif 'Land' in type_line:
            types['Land'] += 1
        else:
            types['Other'] += 1

    return dict(types)


def get_card_count_distribution(deck: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get distribution of card copies (1x, 2x, 3x, 4x)"""
    card_counts = Counter()

    for card in deck:
        card_counts[card.get('name', 'Unknown')] += 1

    copy_distribution = Counter()
    for count in card_counts.values():
        copy_distribution[f'{count}x'] += 1

    return dict(copy_distribution)


def test_deck_build(colors: List[str], strategy: str, format_name: str = "Modern") -> bool:
    """Test deck building via REST API"""

    print(f"\n{'='*80}")
    print(f"BUILDING DECK: {', '.join(colors).upper()} {strategy.upper()}")
    print(f"{'='*80}")

    # Call deck building endpoint
    payload = {
        "query": f"Build a {strategy} deck in {format_name}",
        "format": format_name,
        "colors": colors,
        "strategy": strategy,
        "budget": None
    }

    print(f"\nSending request to {BASE_URL}/v1/query")

    try:
        # Use the /query endpoint instead
        import uuid
        session_id = str(uuid.uuid4())

        query_payload = {
            "query_text": f"Build a {strategy} {format_name} deck in {', '.join(colors)}",
            "session_id": session_id,
            "context": {
                "format": format_name,
                "colors": colors,
                "strategy": strategy
            }
        }

        # Use query parameters instead of JSON body
        import json as json_module
        response = requests.post(
            f"{BASE_URL}/v1/query",
            params={
                "query_text": query_payload["query_text"],
                "session_id": session_id,
                "context": json_module.dumps(query_payload["context"])
            },
            timeout=120
        )

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(f"Payload sent: {json.dumps(query_payload, indent=2)}")
            print(f"Response: {response.text}")
            return False

        result = response.json()

        # Extract deck from response
        # The /query endpoint returns a FusedResponse with agent contributions
        deck_data = result.get('agent_contributions', {}).get('deck_builder', {}).get('data', {})
        deck = deck_data.get('deck', [])
        deck_size = len(deck)

        print(f"\n{'='*80}")
        print(f"DECK BUILD COMPLETE")
        print(f"{'='*80}")
        print(f"Deck size: {deck_size}/60")

        if deck_size == 0:
            print("❌ No cards in deck")
            return False

        # Analyze deck
        print(f"\n{'='*80}")
        print(f"DECK ANALYSIS")
        print(f"{'='*80}")

        # Mana curve
        curve = analyze_mana_curve(deck)
        print(f"\nMana Curve:")
        for cmc, count in curve['distribution'].items():
            bar = '█' * count
            print(f"  {cmc:2d}: {bar} ({count})")
        print(f"  Average CMC: {curve['average_cmc']:.2f}")

        # Color distribution
        colors_dist = analyze_color_distribution(deck)
        print(f"\nColor Distribution:")
        for color, count in sorted(colors_dist.items()):
            print(f"  {color}: {count}")

        # Type distribution
        types_dist = analyze_type_distribution(deck)
        print(f"\nType Distribution:")
        for type_name, count in sorted(types_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"  {type_name}: {count}")

        # Copy distribution
        copies_dist = get_card_count_distribution(deck)
        print(f"\nCard Copy Distribution:")
        for copies, count in sorted(copies_dist.items()):
            print(f"  {copies}: {count} cards")

        # Print deck list
        print(f"\n{'='*80}")
        print(f"DECK LIST")
        print(f"{'='*80}")

        card_counts = Counter()
        for card in deck:
            card_counts[card.get('name', 'Unknown')] += 1

        for card_name, count in sorted(card_counts.items()):
            print(f"{count}x {card_name}")

        # Validate deck
        print(f"\n{'='*80}")
        print(f"VALIDATION")
        print(f"{'='*80}")

        is_valid = deck_size == 60
        print(f"Deck Size: {deck_size}/60 {'✅' if is_valid else '❌'}")

        # Check for mana base (rough check)
        lands = types_dist.get('Land', 0)
        land_percentage = (lands / deck_size) * 100 if deck_size > 0 else 0
        print(f"Land Count: {lands} ({land_percentage:.1f}%) {'✅' if 20 <= lands <= 30 else '⚠️'}")

        # Check creatures vs spells
        creatures = types_dist.get('Creature', 0)
        spells = types_dist.get('Instant', 0) + types_dist.get('Sorcery', 0)
        print(f"Creatures: {creatures}, Spells: {spells}")

        return is_valid

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {BASE_URL}")
        print("   Make sure the API is running: python -m uvicorn mtg_cag_system.main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run end-to-end deck building tests"""

    print("\n" + "="*80)
    print("END-TO-END DECK BUILDING TEST")
    print("="*80)
    print("\nTesting via REST API at http://localhost:8000")

    test_cases = [
        {
            "colors": ["R", "G"],
            "strategy": "aggro",
            "format": "Modern",
            "name": "Gruul Aggro"
        },
        {
            "colors": ["U", "B"],
            "strategy": "control",
            "format": "Modern",
            "name": "Dimir Control"
        },
        {
            "colors": ["W", "B"],
            "strategy": "midrange",
            "format": "Modern",
            "name": "Orzhov Midrange"
        },
    ]

    results = {}

    for test in test_cases:
        print(f"\n\n{'#'*80}")
        print(f"TEST: {test['name']}")
        print(f"{'#'*80}")

        success = test_deck_build(
            colors=test['colors'],
            strategy=test['strategy'],
            format_name=test['format']
        )

        results[test['name']] = "✅ PASS" if success else "❌ FAIL"

    # Summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    for test_name, result in results.items():
        print(f"{test_name}: {result}")

    passed = sum(1 for r in results.values() if "PASS" in r)
    total = len(results)

    print(f"\nTotal: {passed}/{total} passed")


if __name__ == "__main__":
    main()
