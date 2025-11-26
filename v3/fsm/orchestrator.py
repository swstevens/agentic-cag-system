"""
FSM Orchestrator for V3 architecture.

Manages the finite state machine execution and coordinates
transitions between the three primary states with iteration support.
"""

from typing import Any, Dict, Optional
from pydantic_graph import Graph
from .states import ParseRequestNode, BuildInitialDeckNode, RefineDeckNode, VerifyQualityNode, StateData
from ..database.database_service import DatabaseService
from ..database.card_repository import CardRepository
from ..services.deck_builder_service import DeckBuilderService
from ..services.quality_verifier_service import QualityVerifierService


class FSMOrchestrator:
    """
    Orchestrates the finite state machine workflow.

    Manages the "Draft-Verify-Refine" workflow:
    1. Parse Request
    2. Build Initial Deck (Draft)
    3. Verify Quality
    4. Refine Deck (if needed)
    """

    def __init__(
        self,
        database_service: Optional[DatabaseService] = None,
        db_path: str = "v3/data/cards.db"
    ):
        """
        Initialize the FSM orchestrator.
        
        Args:
            database_service: Optional database service instance
            db_path: Path to database file (used if database_service not provided)
        """
        # Initialize database and services
        self.db_service = database_service or DatabaseService(db_path)
        self.card_repo = CardRepository(self.db_service)
        self.deck_builder = DeckBuilderService(self.card_repo)
        self.quality_verifier = QualityVerifierService()
        
        # Create the graph with ALL node types
        self.graph = Graph(nodes=[
            ParseRequestNode, 
            BuildInitialDeckNode, 
            RefineDeckNode, 
            VerifyQualityNode
        ])

    async def execute(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the FSM with the given request data.

        Args:
            request_data: The incoming request data

        Returns:
            Dictionary containing execution results
        """
        state = StateData()

        # Create dependencies dict with services
        deps = {
            "deck_builder": self.deck_builder,
            "quality_verifier": self.quality_verifier,
            "card_repository": self.card_repo,
            "database_service": self.db_service,
        }

        # Create and run the FSM graph
        graph_result = await self.graph.run(
            ParseRequestNode(raw_input=request_data),
            state=state,
            deps=deps,
        )

        # Extract data from GraphRunResult.output (which is the End node data)
        result_data = graph_result.output if hasattr(graph_result, 'output') else {}
        
        return {
            "success": result_data.get("success", False),
            "data": result_data if result_data.get("success") else None,
            "error": result_data.get("error"),
            "errors": state.errors,
        }

