"""
Test script to verify dynamic prompt generation.

This script generates and displays prompts for different formats
to verify they contain correct format-specific information.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from v3.services.prompt_builder import PromptBuilder
from v3.models.format_rules import FormatRules


def test_prompt_generation():
    """Test prompt generation for different formats."""

    formats_to_test = ["Standard", "Commander", "Modern"]

    print("=" * 80)
    print("DYNAMIC PROMPT GENERATION TEST")
    print("=" * 80)

    for format_name in formats_to_test:
        print(f"\n{'=' * 80}")
        print(f"FORMAT: {format_name}")
        print(f"{'=' * 80}")

        # Get format rules for verification
        rules = FormatRules.get_rules(format_name)
        print(f"\nFormat Rules:")
        print(f"  - Deck Size: {rules['deck_size_max']} cards")
        print(f"  - Copy Limit: {rules['copy_limit']}")
        print(f"  - Singleton: {rules['singleton_rule']}")
        print(f"  - Legendary Max: {rules['legendary_max']}")

        # Generate deck builder prompt
        print(f"\n{'-' * 80}")
        print("DECK BUILDER SYSTEM PROMPT:")
        print(f"{'-' * 80}")
        builder_prompt = PromptBuilder.build_deck_builder_system_prompt(format_name)

        # Display key sections
        print(builder_prompt[:1500])  # First 1500 chars
        print("\n... [truncated] ...\n")

        # Verify format-specific content is present
        print("\nVerification:")
        checks = [
            (str(rules['deck_size_max']), f"✓ Contains deck size ({rules['deck_size_max']})"),
            (str(rules['copy_limit']), f"✓ Contains copy limit ({rules['copy_limit']})"),
            (format_name, f"✓ Contains format name ({format_name})"),
        ]

        for check_str, success_msg in checks:
            if check_str in builder_prompt:
                print(f"  {success_msg}")
            else:
                print(f"  ✗ MISSING: {check_str}")

        # Check archetype-specific land counts
        archetype_lands = FormatRules.ARCHETYPE_LAND_COUNTS.get(format_name, {})
        if archetype_lands:
            aggro_lands = archetype_lands.get("Aggro")
            if aggro_lands and str(aggro_lands) in builder_prompt:
                print(f"  ✓ Contains Aggro land count ({aggro_lands})")
            else:
                print(f"  ⚠ Aggro land count not clearly visible")

        print(f"\n{'-' * 80}")
        print("REFINE AGENT SYSTEM PROMPT:")
        print(f"{'-' * 80}")
        refine_prompt = PromptBuilder.build_refine_agent_system_prompt(format_name)
        print(refine_prompt[:1000])  # First 1000 chars
        print("\n... [truncated] ...\n")

        print(f"\n{'-' * 80}")
        print("LLM ANALYZER SYSTEM PROMPT:")
        print(f"{'-' * 80}")
        analyzer_prompt = PromptBuilder.build_llm_analyzer_system_prompt(format_name)
        print(analyzer_prompt[:1000])  # First 1000 chars
        print("\n... [truncated] ...\n")


def test_format_specific_differences():
    """Test that Commander and Standard prompts are meaningfully different."""

    print("\n" + "=" * 80)
    print("FORMAT COMPARISON: Standard vs Commander")
    print("=" * 80)

    standard_prompt = PromptBuilder.build_deck_builder_system_prompt("Standard")
    commander_prompt = PromptBuilder.build_deck_builder_system_prompt("Commander")

    print("\nStandard-specific content:")
    standard_specific = [
        "60-card",
        "22-24 lands",  # Aggro lands for Standard
        "4 copies",
    ]

    for content in standard_specific:
        if content.lower() in standard_prompt.lower():
            print(f"  ✓ Contains: {content}")
        else:
            print(f"  ✗ Missing: {content}")

    print("\nCommander-specific content:")
    commander_specific = [
        "100-card",
        "35-38 lands",  # Approximate range
        "singleton",
        "1 copy",
    ]

    for content in commander_specific:
        if content.lower() in commander_prompt.lower():
            print(f"  ✓ Contains: {content}")
        else:
            print(f"  ✗ Missing: {content}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_prompt_generation()
    test_format_specific_differences()
