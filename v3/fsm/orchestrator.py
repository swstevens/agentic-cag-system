"""
FSM Orchestrator for V3 architecture.

Manages the finite state machine execution and coordinates
transitions between the three primary states with iteration support.
"""

from typing import Any, Dict, Optional, Union
from pydantic_graph import Graph
from .states import ParseRequestNode, BuildInitialDeckNode, RefineDeckNode, VerifyQualityNode, UserModificationNode, StateData
from ..database.database_service import DatabaseService
from ..database.card_repository import CardRepository
from ..services.deck_builder_service import DeckBuilderService
from ..services.quality_verifier_service import QualityVerifierService
from ..services.vector_service import VectorService
from ..models.deck import DeckModificationRequest, Deck


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
        
        # Initialize Vector Service
        try:
            self.vector_service = VectorService()
            print("✓ Vector service initialized")
        except Exception as e:
            print(f"Warning: Failed to initialize VectorService: {e}")
            self.vector_service = None
            
        self.card_repo = CardRepository(self.db_service, vector_service=self.vector_service)
        self.deck_builder = DeckBuilderService(self.card_repo)
        
        # Initialize LLM service
        try:
            from ..services.llm_service import LLMService
            self.llm_service = LLMService()
        except Exception as e:
            print(f"Warning: Failed to initialize LLMService: {e}")
            self.llm_service = None
            
        self.quality_verifier = QualityVerifierService(self.llm_service)
        
        # Initialize agent-based deck builder
        try:
            from ..services.agent_deck_builder_service import AgentDeckBuilderService
            self.agent_deck_builder = AgentDeckBuilderService(self.card_repo)
            print("✓ Agent-based deck builder initialized")
        except Exception as e:
            print(f"Warning: Failed to initialize AgentDeckBuilderService: {e}")
            self.agent_deck_builder = None
        
        # Create the graph with ALL node types
        self.graph = Graph(nodes=[
            ParseRequestNode, 
            BuildInitialDeckNode, 
            RefineDeckNode, 
            VerifyQualityNode
        ])

    async def execute(self, request_data: Union[Dict[str, Any], DeckModificationRequest]) -> Dict[str, Any]:
        """
        Execute the FSM with the given request data.

        Routes to either:
        - New deck build flow (if dict with "message")
        - Deck modification flow (if DeckModificationRequest)

        Args:
            request_data: Either dict for new deck OR DeckModificationRequest for modification

        Returns:
            Dictionary containing execution results
        """
        # Simple routing: check request type
        if isinstance(request_data, DeckModificationRequest):
            return await self._execute_modification(request_data)
        else:
            return await self._execute_new_deck(request_data)

    async def _execute_new_deck(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute new deck building flow."""
        state = StateData()

        # Create dependencies dict with services
        deps = {
            "deck_builder": self.deck_builder,
            "agent_deck_builder": self.agent_deck_builder,
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

    async def _execute_modification(self, mod_request: DeckModificationRequest) -> Dict[str, Any]:
        """Execute deck modification flow."""
        # Create modification node
        mod_node = UserModificationNode()

        # Execute modification directly (not part of FSM graph)
        result = await mod_node.execute(
            mod_request=mod_request,
            agent_deck_builder=self.agent_deck_builder,
            quality_verifier=self.quality_verifier,
            card_repo=self.card_repo
        )

        return result

