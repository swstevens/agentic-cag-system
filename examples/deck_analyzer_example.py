"""
Example: Using the DeckAnalyzerAgent

This example demonstrates how to use the LLM-based DeckAnalyzerAgent
to get comprehensive deck analysis with structured outputs.
"""

import asyncio
import os
from mtg_cag_system.agents.deck_analyzer_agent import DeckAnalyzerAgent


async def main():
    # Ensure you have OPENAI_API_KEY set in your environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Initialize the agent
    analyzer = DeckAnalyzerAgent(model_name="openai:gpt-4")

    # Example deck: Mono-Red Aggro (Modern)
    sample_deck = [
        {"name": "Monastery Swiftspear", "cmc": 1, "type_line": "Creature — Human Monk",
         "oracle_text": "Haste, Prowess", "colors": ["R"]},
        {"name": "Monastery Swiftspear", "cmc": 1, "type_line": "Creature — Human Monk",
         "oracle_text": "Haste, Prowess", "colors": ["R"]},
        {"name": "Monastery Swiftspear", "cmc": 1, "type_line": "Creature — Human Monk",
         "oracle_text": "Haste, Prowess", "colors": ["R"]},
        {"name": "Monastery Swiftspear", "cmc": 1, "type_line": "Creature — Human Monk",
         "oracle_text": "Haste, Prowess", "colors": ["R"]},
        {"name": "Goblin Guide", "cmc": 1, "type_line": "Creature — Goblin Scout",
         "oracle_text": "Haste", "colors": ["R"]},
        {"name": "Goblin Guide", "cmc": 1, "type_line": "Creature — Goblin Scout",
         "oracle_text": "Haste", "colors": ["R"]},
        {"name": "Goblin Guide", "cmc": 1, "type_line": "Creature — Goblin Scout",
         "oracle_text": "Haste", "colors": ["R"]},
        {"name": "Goblin Guide", "cmc": 1, "type_line": "Creature — Goblin Scout",
         "oracle_text": "Haste", "colors": ["R"]},
        {"name": "Lightning Bolt", "cmc": 1, "type_line": "Instant",
         "oracle_text": "Lightning Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Lightning Bolt", "cmc": 1, "type_line": "Instant",
         "oracle_text": "Lightning Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Lightning Bolt", "cmc": 1, "type_line": "Instant",
         "oracle_text": "Lightning Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Lightning Bolt", "cmc": 1, "type_line": "Instant",
         "oracle_text": "Lightning Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Lava Spike", "cmc": 1, "type_line": "Sorcery",
         "oracle_text": "Lava Spike deals 3 damage to target player or planeswalker.", "colors": ["R"]},
        {"name": "Lava Spike", "cmc": 1, "type_line": "Sorcery",
         "oracle_text": "Lava Spike deals 3 damage to target player or planeswalker.", "colors": ["R"]},
        {"name": "Lava Spike", "cmc": 1, "type_line": "Sorcery",
         "oracle_text": "Lava Spike deals 3 damage to target player or planeswalker.", "colors": ["R"]},
        {"name": "Lava Spike", "cmc": 1, "type_line": "Sorcery",
         "oracle_text": "Lava Spike deals 3 damage to target player or planeswalker.", "colors": ["R"]},
        {"name": "Rift Bolt", "cmc": 3, "type_line": "Sorcery",
         "oracle_text": "Rift Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Rift Bolt", "cmc": 3, "type_line": "Sorcery",
         "oracle_text": "Rift Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Rift Bolt", "cmc": 3, "type_line": "Sorcery",
         "oracle_text": "Rift Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Rift Bolt", "cmc": 3, "type_line": "Sorcery",
         "oracle_text": "Rift Bolt deals 3 damage to any target.", "colors": ["R"]},
        # 20 Mountains
        *[{"name": "Mountain", "cmc": 0, "type_line": "Basic Land — Mountain",
           "oracle_text": "Tap: Add R.", "colors": []} for _ in range(20)]
    ]

    print("=" * 80)
    print("DECK ANALYSIS EXAMPLE")
    print("=" * 80)
    print("\nAnalyzing Mono-Red Aggro deck...\n")

    # Analyze the deck using the convenience method
    result = await analyzer.analyze_full_deck(
        cards=sample_deck,
        archetype="aggro",
        deck_format="Modern",
        deck_size=60
    )

    # Print results
    print(f"\n{'=' * 80}")
    print("ANALYSIS RESULTS")
    print(f"{'=' * 80}\n")

    print(f"Overall Score: {result['overall_score']}/100")
    print(f"\n{result['overall_assessment']}\n")

    print(f"\n--- Mana Curve ---")
    mana_curve = result['mana_curve']
    print(f"Average CMC: {mana_curve['average_cmc']:.2f}")
    print(f"Curve Quality: {mana_curve['curve_quality']}")
    if mana_curve['recommendations']:
        print("Recommendations:")
        for rec in mana_curve['recommendations']:
            print(f"  - {rec}")

    print(f"\n--- Land Ratio ---")
    land_ratio = result['land_ratio']
    print(f"Lands: {land_ratio['land_count']} ({land_ratio['land_percentage']:.1f}%)")
    print(f"Quality: {land_ratio['ratio_quality']}")
    if land_ratio.get('recommended_land_count'):
        print(f"Recommended: {land_ratio['recommended_land_count']} lands")

    print(f"\n--- Synergies ---")
    synergies = result['synergies']
    if synergies:
        for syn in synergies:
            print(f"- {syn['name']} ({syn['strength']})")
            print(f"  Cards: {', '.join(syn['card_names'])}")
            print(f"  {syn['description']}")
    else:
        print("No specific synergies detected")

    print(f"\n--- Win Conditions ---")
    win_conds = result['win_conditions']
    print(f"Quality: {win_conds['win_condition_quality']}")
    print(f"Primary Win Conditions:")
    for wc in win_conds['primary_win_conditions']:
        print(f"  - {wc}")
    if win_conds.get('backup_win_conditions'):
        print(f"Backup Win Conditions:")
        for wc in win_conds['backup_win_conditions']:
            print(f"  - {wc}")

    print(f"\n--- Archetype Consistency ---")
    arch = result['archetype_consistency']
    print(f"Archetype: {arch['declared_archetype']}")
    print(f"Consistency Score: {arch['consistency_score']:.2f}/1.0")
    print(f"Strengths:")
    for strength in arch['archetype_strengths']:
        print(f"  + {strength}")
    if arch['archetype_weaknesses']:
        print(f"Weaknesses:")
        for weakness in arch['archetype_weaknesses']:
            print(f"  - {weakness}")

    print(f"\n--- Priority Improvements ---")
    for i, improvement in enumerate(result['priority_improvements'], 1):
        print(f"{i}. {improvement}")

    print(f"\n--- Competitive Assessment ---")
    print(f"Is Competitive: {result['is_competitive']}")
    print(f"Needs Major Changes: {result['needs_major_changes']}")

    print(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())
