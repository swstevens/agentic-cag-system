import asyncio
import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import AsyncMock, MagicMock
from v3.models.deck import Deck, DeckImprovementPlan, CardRemoval, CardSuggestion, DeckCard, MTGCard
from v3.services.quality_verifier_service import QualityVerifierService
from v3.services.deck_builder_service import DeckBuilderService
from v3.services.llm_service import LLMService

class TestLLMIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_quality_verifier_uses_llm_plan(self):
        print("Testing QualityVerifierService integration...")
        # Mock LLM Service
        mock_llm = MagicMock(spec=LLMService)
        mock_plan = DeckImprovementPlan(
            removals=[CardRemoval(card_name="Weak Card", reason="Bad", quantity=2)],
            additions=[CardSuggestion(card_name="Strong Card", reason="Good", quantity=2)],
            analysis="Test Analysis"
        )
        mock_llm.analyze_deck = AsyncMock(return_value=mock_plan)
        
        # Setup Service
        verifier = QualityVerifierService(llm_service=mock_llm)
        deck = Deck(format="Standard", cards=[])
        
        # Run Verification
        metrics = await verifier.verify_deck(deck)
        
        # Assertions
        self.assertEqual(metrics.improvement_plan, mock_plan)
        self.assertTrue(any("LLM Analysis: Test Analysis" in s for s in metrics.suggestions))
        self.assertTrue(any("Remove 2x Weak Card: Bad" in s for s in metrics.suggestions))
        self.assertTrue(any("Add 2x Strong Card: Good" in s for s in metrics.suggestions))
        print("✓ QualityVerifierService test passed")

    async def test_deck_builder_executes_plan(self):
        print("Testing DeckBuilderService integration...")
        # Setup Mocks
        mock_repo = MagicMock()
        # Mock search to return a card for "Strong Card"
        strong_card = MTGCard(id="1", name="Strong Card", type_line="Creature", cmc=2.0)
        mock_repo.get_by_name.return_value = strong_card
        
        builder = DeckBuilderService(card_repository=mock_repo)
        
        # Setup Deck
        weak_card = MTGCard(id="2", name="Weak Card", type_line="Creature", cmc=1.0)
        deck = Deck(
            format="Standard",
            cards=[DeckCard(card=weak_card, quantity=4)]
        )
        
        # Setup Plan
        plan = DeckImprovementPlan(
            removals=[CardRemoval(card_name="Weak Card", reason="Bad", quantity=2)],
            additions=[CardSuggestion(card_name="Strong Card", reason="Good", quantity=2)],
            analysis="Test Analysis"
        )
        
        # Run Refine
        refined_deck = builder.refine_deck(deck, [], MagicMock(), improvement_plan=plan)
        
        # Assertions
        # Should have 2 Weak Cards left (4 - 2)
        weak_cards = [dc for dc in refined_deck.cards if dc.card.name == "Weak Card"]
        self.assertEqual(len(weak_cards), 1)
        self.assertEqual(weak_cards[0].quantity, 2)
        
        # Should have 2 Strong Cards added
        strong_cards = [dc for dc in refined_deck.cards if dc.card.name == "Strong Card"]
        self.assertEqual(len(strong_cards), 1)
        self.assertEqual(strong_cards[0].quantity, 2)
        print("✓ DeckBuilderService test passed")

if __name__ == "__main__":
    unittest.main()
