"""
Tests for the DeckAnalyzerAgent

Tests the LLM-based deck analysis functionality.
"""

import pytest
import os
from mtg_cag_system.agents.deck_analyzer_agent import DeckAnalyzerAgent


@pytest.fixture
def sample_mono_red_aggro():
    """Sample mono-red aggro deck"""
    return [
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


@pytest.fixture
def sample_poor_deck():
    """Sample poorly constructed deck"""
    return [
        {"name": "Llanowar Elves", "cmc": 1, "type_line": "Creature — Elf Druid",
         "oracle_text": "Tap: Add G.", "colors": ["G"]},
        {"name": "Birds of Paradise", "cmc": 1, "type_line": "Creature — Bird",
         "oracle_text": "Flying. Tap: Add one mana of any color.", "colors": ["G"]},
        {"name": "Tarmogoyf", "cmc": 2, "type_line": "Creature — Lhurgoyf",
         "oracle_text": "Tarmogoyf's power is equal to the number of card types...", "colors": ["G"]},
        {"name": "Snapcaster Mage", "cmc": 2, "type_line": "Creature — Human Wizard",
         "oracle_text": "Flash. When Snapcaster Mage enters...", "colors": ["U"]},
        {"name": "Lightning Bolt", "cmc": 1, "type_line": "Instant",
         "oracle_text": "Lightning Bolt deals 3 damage to any target.", "colors": ["R"]},
        {"name": "Counterspell", "cmc": 2, "type_line": "Instant",
         "oracle_text": "Counter target spell.", "colors": ["U"]},
        {"name": "Path to Exile", "cmc": 1, "type_line": "Instant",
         "oracle_text": "Exile target creature...", "colors": ["W"]},
        {"name": "Wrath of God", "cmc": 4, "type_line": "Sorcery",
         "oracle_text": "Destroy all creatures...", "colors": ["W"]},
        {"name": "Emrakul, the Aeons Torn", "cmc": 15, "type_line": "Legendary Creature — Eldrazi",
         "oracle_text": "Protection from colored spells...", "colors": []},
        # Way too many lands (30)
        *[{"name": "Forest", "cmc": 0, "type_line": "Basic Land — Forest",
           "oracle_text": "Tap: Add G.", "colors": []} for _ in range(10)],
        *[{"name": "Island", "cmc": 0, "type_line": "Basic Land — Island",
           "oracle_text": "Tap: Add U.", "colors": []} for _ in range(10)],
        *[{"name": "Mountain", "cmc": 0, "type_line": "Basic Land — Mountain",
           "oracle_text": "Tap: Add R.", "colors": []} for _ in range(10)]
    ]


@pytest.mark.asyncio
async def test_analyzer_agent_initialization():
    """Test that the DeckAnalyzerAgent initializes correctly"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")
    assert agent is not None
    assert agent._pydantic_agent is not None
    assert agent.agent_type is not None


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
async def test_analyze_good_aggro_deck(sample_mono_red_aggro):
    """Test analysis of a well-constructed aggro deck"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")

    response = await agent.process({
        "cards": sample_mono_red_aggro,
        "archetype": "aggro",
        "format": "Modern",
        "deck_size": 60
    })

    assert response.success is True
    assert "overall_score" in response.data

    # Good aggro deck should score reasonably well
    assert response.data["overall_score"] >= 70

    # Should identify aggro archetype consistency
    assert "archetype_consistency" in response.data
    consistency = response.data["archetype_consistency"]
    assert consistency["consistency_score"] >= 0.7

    # Should identify prowess synergy
    assert "synergies" in response.data
    synergies = response.data["synergies"]
    assert len(synergies) > 0

    # Should identify win condition
    assert "win_conditions" in response.data
    win_conds = response.data["win_conditions"]
    assert len(win_conds["primary_win_conditions"]) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
async def test_analyze_poor_deck(sample_poor_deck):
    """Test analysis of a poorly constructed deck"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")

    response = await agent.process({
        "cards": sample_poor_deck,
        "archetype": "midrange",
        "format": "Modern",
        "deck_size": 60
    })

    assert response.success is True
    assert "overall_score" in response.data

    # Poor deck should score low
    assert response.data["overall_score"] <= 50

    # Should identify major issues
    assert "needs_major_changes" in response.data
    assert response.data["needs_major_changes"] is True

    # Should have low competitive viability
    assert "is_competitive" in response.data
    assert response.data["is_competitive"] is False

    # Should identify land ratio problem
    assert "land_ratio" in response.data
    land_ratio = response.data["land_ratio"]
    ratio_quality = land_ratio["ratio_quality"]
    assert "too_many" in ratio_quality.lower()


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
async def test_analyze_full_deck_convenience_method(sample_mono_red_aggro):
    """Test the convenience method for deck analysis"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")

    result = await agent.analyze_full_deck(
        cards=sample_mono_red_aggro,
        archetype="aggro",
        deck_format="Modern",
        deck_size=60
    )

    assert "overall_score" in result
    assert "overall_assessment" in result
    assert "mana_curve" in result
    assert "land_ratio" in result


@pytest.mark.asyncio
async def test_build_analysis_prompt(sample_mono_red_aggro):
    """Test that analysis prompt is built correctly"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")

    prompt = agent._build_analysis_prompt(
        cards=sample_mono_red_aggro,
        archetype="aggro",
        deck_format="Modern",
        deck_size=60
    )

    assert "Modern" in prompt
    assert "aggro" in prompt
    assert "Monastery Swiftspear" in prompt
    assert "CMC:" in prompt
    assert "60 cards" in prompt


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
async def test_mana_curve_analysis(sample_mono_red_aggro):
    """Test that mana curve is analyzed correctly"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")

    result = await agent.analyze_full_deck(
        cards=sample_mono_red_aggro,
        archetype="aggro",
        deck_format="Modern",
        deck_size=60
    )

    mana_curve = result["mana_curve"]
    assert "average_cmc" in mana_curve
    assert "curve_quality" in mana_curve

    # Aggro deck should have low average CMC
    assert mana_curve["average_cmc"] <= 2.5


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No OpenAI API key")
async def test_priority_improvements_provided(sample_poor_deck):
    """Test that priority improvements are provided"""
    agent = DeckAnalyzerAgent(model_name="openai:gpt-4")

    result = await agent.analyze_full_deck(
        cards=sample_poor_deck,
        archetype="midrange",
        deck_format="Modern",
        deck_size=60
    )

    assert "priority_improvements" in result
    improvements = result["priority_improvements"]
    assert len(improvements) > 0
    # Should have actionable suggestions
    assert all(isinstance(imp, str) and len(imp) > 10 for imp in improvements)
