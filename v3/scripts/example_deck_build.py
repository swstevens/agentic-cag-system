"""
Example usage of the V3 FSM-based deck building system.

This demonstrates how to use the orchestrator to build a deck
with iterative quality refinement.
"""

import asyncio
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from v3.fsm.orchestrator import FSMOrchestrator


async def main():
    """Run example deck building request."""
    
    # Initialize orchestrator
    orchestrator = FSMOrchestrator()
    
    # Example request: Build a red aggro deck for Standard
    request = {
        "format": "Standard",
        "colors": ["R"],
        "archetype": "Aggro",
        "strategy": "Fast, aggressive creatures with burn spells",
        "quality_threshold": 0.7,
        "max_iterations": 5,
        "deck_size": 60,
    }
    
    print("Building deck with the following parameters:")
    print(json.dumps(request, indent=2))
    print("\n" + "="*60 + "\n")
    
    # Execute FSM
    result = await orchestrator.execute(request)
    
    # Display results
    if result["success"]:
        print("✓ Deck building successful!\n")
        
        data = result["data"]
        
        print(f"Iterations: {data['iteration_count']}")
        print(f"Final Quality Score: {data['quality_metrics']['overall_score']:.2f}\n")
        
        print("Quality Breakdown:")
        metrics = data['quality_metrics']
        print(f"  - Mana Curve: {metrics['mana_curve_score']:.2f}")
        print(f"  - Land Ratio: {metrics['land_ratio_score']:.2f}")
        print(f"  - Synergy: {metrics['synergy_score']:.2f}")
        print(f"  - Consistency: {metrics['consistency_score']:.2f}")
        print()
        
        if metrics['issues']:
            print("Issues Identified:")
            for issue in metrics['issues']:
                print(f"  - {issue}")
            print()
        
        if metrics['suggestions']:
            print("Suggestions:")
            for suggestion in metrics['suggestions']:
                print(f"  - {suggestion}")
            print()
        
        print("\nIteration History:")
        for record in data['iteration_history']:
            print(f"  Iteration {record['iteration']}: Quality {record['quality_score']:.2f}")
        
        print("\n" + "="*60 + "\n")
        
        # Display cache statistics (CAG performance)
        cache_stats = orchestrator.card_repo.get_cache_stats()
        print("CAG (Cache-Augmented Generation) Statistics:")
        print(f"  Cache Hits: {cache_stats['hits']}")
        print(f"  Cache Misses: {cache_stats['misses']}")
        print(f"  Hit Rate: {cache_stats['hit_rate'] * 100:.1f}%")
        print(f"  Cache Size: {cache_stats['size']} cards")
        print(f"  Evictions: {cache_stats['evictions']}")
        print()
        print("Note: Higher hit rate = better CAG performance!")
        
        print("\n" + "="*60 + "\n")
        
        deck = data['deck']
        print(f"Final Deck ({deck['total_cards']} cards):")
        print(f"Format: {deck['format']}")
        print(f"Colors: {', '.join(deck['colors']) if deck['colors'] else 'Colorless'}")
        print(f"Archetype: {deck['archetype']}\n")
        
        print("Decklist:")
        for deck_card in deck['cards']:
            card = deck_card['card']
            quantity = deck_card['quantity']
            print(f"  {quantity}x {card['name']} ({card['type_line']})")
    else:
        print("✗ Deck building failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(main())
