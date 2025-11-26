#!/usr/bin/env python3
"""
Test script to verify the full API workflow with SQLAlchemy integration
Tests the entire stack: API -> Services -> SQLAlchemy -> Database
"""

import sys
import time
import requests
from pathlib import Path
import subprocess
import signal

# Test configuration
API_BASE_URL = "http://localhost:8000"
API_V1_URL = f"{API_BASE_URL}/api/v1"


def wait_for_server(timeout=30):
    """Wait for the API server to be ready"""
    print("Waiting for server to start...", end="", flush=True)
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print(" [OK]")
                return True
        except requests.exceptions.RequestException:
            pass

        print(".", end="", flush=True)
        time.sleep(1)

    print(" [TIMEOUT]")
    return False


def test_health_check():
    """Test 1: Health check endpoint"""
    print("\n" + "="*70)
    print("Test 1: Health Check")
    print("="*70)

    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response: {data}")
            print("[OK] Health check passed")
            return True
        else:
            print(f"[ERROR] Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return False


def test_get_card_by_name():
    """Test 2: Get specific card by name (tests database integration)"""
    print("\n" + "="*70)
    print("Test 2: Get Card by Name (SQLAlchemy -> Database)")
    print("="*70)

    card_name = "Lightning Bolt"
    print(f"Fetching card: {card_name}")

    try:
        response = requests.get(f"{API_V1_URL}/cards/{card_name}")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            card = response.json()
            print(f"\n[OK] Found card: {card['name']}")
            print(f"  - Mana Cost: {card['mana_cost']}")
            print(f"  - Type: {card['type_line']}")
            print(f"  - Oracle Text: {card['oracle_text']}")
            print(f"  - Colors: {card['colors']}")
            print(f"  - CMC: {card['cmc']}")
            print(f"  - Set: {card['set_code']}")
            print(f"  - Rarity: {card['rarity']}")
            return True
        else:
            print(f"[ERROR] Failed to get card: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to get card: {e}")
        return False


def test_search_cards():
    """Test 3: Search cards with filters (tests query building)"""
    print("\n" + "="*70)
    print("Test 3: Search Cards with Filters")
    print("="*70)

    # Test fuzzy search
    print("Searching for cards with 'counterspell' in name...")

    try:
        params = {
            "query": "counterspell",
            "limit": 5
        }
        response = requests.get(f"{API_V1_URL}/cards", params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            cards = response.json()
            print(f"\n[OK] Found {len(cards)} cards:")
            for card in cards:
                print(f"  - {card['name']} ({card['set_code']})")
            return True
        else:
            print(f"[ERROR] Search failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        return False


def test_search_with_filters():
    """Test 4: Search with color and type filters"""
    print("\n" + "="*70)
    print("Test 4: Search with Color and Type Filters")
    print("="*70)

    print("Searching for red creatures...")

    try:
        params = {
            "query": "",
            "colors": ["R"],
            "types": ["Creature"],
            "limit": 5
        }
        response = requests.get(f"{API_V1_URL}/cards", params=params)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            cards = response.json()
            print(f"\n[OK] Found {len(cards)} red creatures:")
            for card in cards:
                print(f"  - {card['name']} (CMC: {card['cmc']}, Colors: {card['colors']})")
            return True
        else:
            print(f"[ERROR] Filtered search failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Filtered search failed: {e}")
        return False


def test_cache_stats():
    """Test 5: Get cache statistics"""
    print("\n" + "="*70)
    print("Test 5: Cache Statistics")
    print("="*70)

    try:
        response = requests.get(f"{API_V1_URL}/cache/stats")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            stats = response.json()
            print(f"\n[OK] Cache Statistics:")
            print(f"  - L1 Size: {stats.get('l1_size', 'N/A')}")
            print(f"  - L2 Size: {stats.get('l2_size', 'N/A')}")
            print(f"  - L3 Size: {stats.get('l3_size', 'N/A')}")
            print(f"  - Total Hits: {stats.get('total_hits', 'N/A')}")
            print(f"  - Total Misses: {stats.get('total_misses', 'N/A')}")
            return True
        else:
            print(f"[ERROR] Cache stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Cache stats failed: {e}")
        return False


def test_agent_status():
    """Test 6: Get agent status"""
    print("\n" + "="*70)
    print("Test 6: Agent Status")
    print("="*70)

    try:
        response = requests.get(f"{API_V1_URL}/agents/status")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            status = response.json()
            print(f"\n[OK] Agent Status:")
            for agent_name, agent_status in status.items():
                print(f"  - {agent_name}: {agent_status}")
            return True
        else:
            print(f"[ERROR] Agent status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Agent status failed: {e}")
        return False


def test_card_not_found():
    """Test 7: Card not found error handling"""
    print("\n" + "="*70)
    print("Test 7: Error Handling (Card Not Found)")
    print("="*70)

    fake_card_name = "This Card Does Not Exist 12345"
    print(f"Attempting to fetch non-existent card: {fake_card_name}")

    try:
        response = requests.get(f"{API_V1_URL}/cards/{fake_card_name}")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 404:
            error = response.json()
            print(f"[OK] Correctly returned 404 error")
            print(f"  Error detail: {error.get('detail', 'N/A')}")
            return True
        else:
            print(f"[ERROR] Expected 404, got {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False


def test_database_integration():
    """Test 8: Verify SQLAlchemy database integration"""
    print("\n" + "="*70)
    print("Test 8: Database Integration (Pydantic <-> SQLAlchemy)")
    print("="*70)

    print("Fetching multiple cards to verify ORM conversion...")

    test_cards = ["Lightning Bolt", "Counterspell", "Black Lotus"]
    success_count = 0

    for card_name in test_cards:
        try:
            response = requests.get(f"{API_V1_URL}/cards/{card_name}")
            if response.status_code == 200:
                card = response.json()
                # Verify Pydantic fields are properly populated
                assert card['id'], "Card ID missing"
                assert card['name'], "Card name missing"
                assert 'colors' in card, "Colors field missing"
                assert 'legalities' in card, "Legalities field missing"
                assert isinstance(card['cmc'], (int, float)), "CMC not a number"

                print(f"  [OK] {card['name']} - All fields validated")
                success_count += 1
            else:
                print(f"  [WARN] {card_name} not found (OK if not in database)")
        except Exception as e:
            print(f"  [ERROR] {card_name} validation failed: {e}")

    print(f"\n[OK] Successfully validated {success_count}/{len(test_cards)} cards")
    return success_count > 0


def run_all_tests():
    """Run all API tests"""
    print("\n")
    print("="*70)
    print("MTG CAG System - Full API Workflow Test")
    print("SQLAlchemy Integration Validation")
    print("="*70)

    # Wait for server to be ready
    if not wait_for_server():
        print("\n[ERROR] Server failed to start within timeout period")
        print("Please start the server manually with:")
        print("  python -m mtg_cag_system.main")
        return False

    # Run tests
    results = []
    results.append(("Health Check", test_health_check()))
    results.append(("Get Card by Name", test_get_card_by_name()))
    results.append(("Search Cards", test_search_cards()))
    results.append(("Search with Filters", test_search_with_filters()))
    results.append(("Cache Statistics", test_cache_stats()))
    results.append(("Agent Status", test_agent_status()))
    results.append(("Error Handling", test_card_not_found()))
    results.append(("Database Integration", test_database_integration()))

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK]" if result else "[FAILED]"
        print(f"{status} {test_name}")

    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)

    return passed == total


if __name__ == "__main__":
    print("\nThis test requires the API server to be running.")
    print("Starting server now...\n")

    # Start the server in background
    server_process = subprocess.Popen(
        [sys.executable, "-m", "mtg_cag_system.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent
    )

    try:
        # Run tests
        success = run_all_tests()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Tests cancelled by user")
        sys.exit(1)

    finally:
        # Stop the server
        print("\nStopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("Server stopped")
