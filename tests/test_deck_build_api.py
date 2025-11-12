#!/usr/bin/env python3
"""
Test the deck building API endpoint
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_deck_build_api():
    """Test the /api/v1/query endpoint for deck building"""

    print("\n" + "="*80)
    print("TESTING DECK BUILD API ENDPOINT")
    print("="*80)

    # Test 1: Simple query via query parameters
    print("\n[Test 1] Testing deck build with query parameters...")
    params = {
        "query_text": "Build a Gruul Aggro deck with 25 iterations",
        "session_id": "test-session-001",
        "context": json.dumps({
            "format": "Modern",
            "colors": ["R", "G"],
            "strategy": "aggro"
        })
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v1/query",
            params=params,
            timeout=120
        )

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")

            # Extract deck info
            deck_data = result.get('agent_contributions', {}).get('deck_builder', {}).get('data', {})
            deck = deck_data.get('deck', [])
            deck_size = len(deck)

            print(f"\nDeck Build Results:")
            print(f"  Deck Size: {deck_size}/60 cards")
            print(f"  Valid: {deck_data.get('valid', False)}")

            # Count card occurrences
            card_counts = {}
            for card in deck:
                card_name = card.get('name', 'Unknown')
                card_counts[card_name] = card_counts.get(card_name, 0) + 1

            print(f"  Unique Cards: {len(card_counts)}")

            # Show first 10 cards
            print(f"\nFirst 10 cards in deck:")
            for i, (card_name, count) in enumerate(list(card_counts.items())[:10], 1):
                print(f"    {count}x {card_name}")

            # Analyze mana curve
            print(f"\nAnalyzing deck composition...")
            types_count = {}
            for card in deck:
                type_line = card.get('type_line', '')
                if 'Creature' in type_line:
                    types_count['Creature'] = types_count.get('Creature', 0) + 1
                elif 'Instant' in type_line:
                    types_count['Instant'] = types_count.get('Instant', 0) + 1
                elif 'Sorcery' in type_line:
                    types_count['Sorcery'] = types_count.get('Sorcery', 0) + 1
                elif 'Land' in type_line:
                    types_count['Land'] = types_count.get('Land', 0) + 1
                else:
                    types_count['Other'] = types_count.get('Other', 0) + 1

            print(f"  Type Distribution:")
            for type_name, count in sorted(types_count.items(), key=lambda x: x[1], reverse=True):
                pct = (count / deck_size * 100) if deck_size > 0 else 0
                print(f"    {type_name}: {count} ({pct:.1f}%)")

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 2: Using the synergy endpoint directly (which we know works)
    print("\n[Test 2] Testing synergy endpoint (known to work)...")
    try:
        response = requests.get(
            f"{BASE_URL}/v1/synergy/Soul%20Warden",
            params={"max_results": 5},
            timeout=30
        )

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            synergies = result.get('synergies', [])
            print(f"Found {len(synergies)} synergies")
            for i, synergy in enumerate(synergies[:3], 1):
                print(f"  {i}. {synergy['name']} (score: {synergy['similarity_score']:.2f})")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test 3: Check health endpoint
    print("\n[Test 3] Checking API health...")
    try:
        response = requests.get(
            f"http://localhost:8000/health",
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API is healthy!")
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ API health check failed")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_deck_build_api()
