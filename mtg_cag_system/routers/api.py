from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
from ..models.card import MTGCard
from ..models.query import UserQuery
from ..models.response import FusedResponse, AgentResponse
from ..models.responses import SynergyLookupResponse
from ..models.agent import AgentState
from ..controllers.orchestrator_v2 import AgentOrchestratorV2


router = APIRouter(prefix="/api/v1", tags=["mtg-cag"])


# Dependency to get orchestrator (will be injected)
async def get_orchestrator() -> AgentOrchestratorV2:
    # This will be set up in main.py
    from ..main import app
    return app.state.orchestrator


@router.post("/query", response_model=FusedResponse)
async def process_query(
    query_text: str,
    session_id: str,
    context: Optional[Dict[str, Any]] = None,
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> FusedResponse:
    """
    Process a user query about MTG deck building

    Args:
        query_text: The user's question
        session_id: Session identifier for context
        context: Optional additional context (filters, preferences)

    Returns:
        FusedResponse with answer and reasoning chain
    """
    user_query = UserQuery(
        session_id=session_id,
        query_text=query_text,
        context=context or {}
    )

    response = await orchestrator.process_query(user_query)
    return response


@router.get("/cards/{card_name}", response_model=MTGCard)
async def get_card(
    card_name: str,
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> MTGCard:
    """
    Get details about a specific card

    Args:
        card_name: Name of the card

    Returns:
        MTGCard model with full card details
    """
    card_lookup = orchestrator.knowledge_agent.card_lookup
    card = card_lookup.get_card(card_name)

    if not card:
        raise HTTPException(status_code=404, detail=f"Card '{card_name}' not found")

    return card


@router.get("/cards", response_model=List[MTGCard])
async def search_cards(
    query: str,
    colors: Optional[List[str]] = None,
    types: Optional[List[str]] = None,
    format_filter: Optional[str] = None,
    limit: int = 20,
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> List[MTGCard]:
    """
    Search for cards matching criteria

    Args:
        query: Search text
        colors: Filter by colors (W, U, B, R, G)
        types: Filter by card types
        format_filter: Filter by format legality
        limit: Maximum results to return

    Returns:
        List of matching MTGCard models
    """
    card_lookup = orchestrator.knowledge_agent.card_lookup

    # If query is provided, use fuzzy search
    if query:
        cards = card_lookup.fuzzy_search(query, limit=limit)
    # If filters are provided without query, use database service directly
    elif card_lookup._CardLookupService__database:
        # Access the database service for filtered searches
        db = card_lookup._CardLookupService__database
        cards = db.search_cards(
            query="",
            colors=colors,
            types=types,
            limit=limit
        )
    else:
        cards = []

    return cards[:limit]


@router.post("/deck/validate", response_model=AgentResponse)
async def validate_deck(
    deck_cards: List[Dict[str, Any]],
    format_name: str = "Standard",
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> AgentResponse:
    """
    Validate a deck using symbolic reasoning

    Args:
        deck_cards: List of cards in the deck
        format_name: Format to validate against

    Returns:
        AgentResponse with validation results
    """
    symbolic_input = {
        "type": "deck_validation",
        "data": {
            "cards": deck_cards,
            "format": format_name
        }
    }

    response = await orchestrator.symbolic_agent.process(symbolic_input)
    return response


@router.get("/cache/stats")
async def get_cache_stats(
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> Dict[str, Any]:
    """Get cache statistics"""
    return orchestrator.cache.get_stats()


@router.post("/cache/clear/{tier}")
async def clear_cache_tier(
    tier: int,
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> Dict[str, str]:
    """Clear a specific cache tier (1, 2, or 3)"""
    if tier not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Tier must be 1, 2, or 3")

    orchestrator.cache.clear_tier(tier)
    return {"message": f"Cache tier {tier} cleared"}


@router.get("/agents/status")
async def get_agent_status(
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> Dict[str, AgentState]:
    """Get status of all agents"""
    return {
        "scheduling": orchestrator.scheduling_agent.get_state(),
        "knowledge_fetch": orchestrator.knowledge_agent.get_state(),
        "symbolic_reasoning": orchestrator.symbolic_agent.get_state()
    }


@router.get("/synergy/{card_name}", response_model=SynergyLookupResponse)
async def lookup_card_synergies(
    card_name: str,
    max_results: int = 10,
    format_filter: Optional[str] = None,
    archetype: Optional[str] = None,
    orchestrator: AgentOrchestratorV2 = Depends(get_orchestrator)
) -> SynergyLookupResponse:
    """
    Look up synergistic cards for a given card using semantic similarity.

    This endpoint finds cards that work well together mechanically and thematically
    using vector embeddings from the ChromaDB semantic store.

    Args:
        card_name: Name of the card to find synergies for (e.g., "Lightning Bolt")
        max_results: Maximum number of synergistic cards to return (default: 10, max: 100)
        format_filter: Optional format to filter results by legality (Standard, Modern, Commander, etc.)
        archetype: Optional archetype for context (aggro, control, midrange, combo, tempo, ramp)

    Returns:
        SynergyLookupResponse with:
        - source_card: The queried card name
        - synergies: List of synergistic cards with similarity scores (0.0-1.0)
        - total_found: Number of synergies returned
        - execution_time: Time taken for the lookup in seconds

    Examples:
        GET /api/v1/synergy/Lightning%20Bolt
        GET /api/v1/synergy/Counterspell?max_results=20&format_filter=Modern
        GET /api/v1/synergy/Goblin%20Electromancer?archetype=aggro&max_results=15
    """
    # Validate max_results
    if max_results < 1 or max_results > 100:
        raise HTTPException(
            status_code=400,
            detail="max_results must be between 1 and 100"
        )

    # Get synergy lookup service from orchestrator
    synergy_service = orchestrator.synergy_lookup_service

    # Process the synergy lookup
    response = await synergy_service.lookup_synergies(
        card_name=card_name,
        max_results=max_results,
        archetype=archetype,
        format_filter=format_filter
    )

    # Validate that card was found
    if response.total_found == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Card '{card_name}' not found or no synergies available"
        )

    return response
