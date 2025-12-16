"""
FSM State definitions using Pydantic's graph module.

This module defines the three primary states of the system:
1. Parse Request/Orchestrator
2. Query Database
3. Verify Quality

With iteration support for quality-driven deck refinement.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pydantic_graph import BaseNode, End, GraphRunContext

from ..models.deck import (
    Deck,
    DeckBuildRequest,
    DeckQualityMetrics,
    IterationState,
    IterationRecord,
    DeckModificationRequest,
    ModificationResult,
    ModificationIntent,
)
from ..services.deck_builder_service import DeckBuilderService
from ..services.quality_verifier_service import QualityVerifierService


@dataclass
class StateData:
    """Shared state data across FSM transitions."""

    # New deck creation fields
    request: Optional[DeckBuildRequest] = None
    current_deck: Optional[Deck] = None
    iteration_state: Optional[IterationState] = None
    latest_quality: Optional[DeckQualityMetrics] = None
    errors: list[str] = field(default_factory=list)

    # Deck modification fields
    modification_request: Optional[DeckModificationRequest] = None
    modification_intent: Optional[ModificationIntent] = None
    modification_result: Optional[ModificationResult] = None
    changes_made: Optional[List[str]] = None
    quality_before: Optional[float] = None


@dataclass
class ParseRequestNode(BaseNode):
    """
    Parse incoming requests and orchestrate workflow.

    This is the entry point state that parses the incoming request
    and determines the workflow parameters.
    """

    raw_input: Dict[str, Any]

    async def run(self, ctx: GraphRunContext[StateData]) -> Union["BuildInitialDeckNode", End]:
        """Parse request and transition to database query state."""
        try:
            # Parse and validate the request
            request = DeckBuildRequest(**self.raw_input)
            ctx.state.request = request

            # Initialize iteration state
            ctx.state.iteration_state = IterationState(
                iteration_count=0,
                max_iterations=request.max_iterations,
                quality_threshold=request.quality_threshold,
                history=[],
            )

            # Transition to build initial deck state
            return BuildInitialDeckNode()
        except Exception as e:
            ctx.state.errors.append(f"Parse request error: {str(e)}")
            return End({"success": False, "error": str(e)})


@dataclass
class BuildInitialDeckNode(BaseNode):
    """
    Build the initial draft of the deck.

    Executes database queries to create a starting point
    based on the user's request and archetype.
    """

    async def run(self, ctx: GraphRunContext[StateData]) -> Union["VerifyQualityNode", End]:
        """Build initial deck draft using LLM agent."""
        try:
            request = ctx.state.request
            if not request:
                raise ValueError("No request found in state")

            # Try agent-based builder first
            agent_builder = ctx.deps.get("agent_deck_builder")
            if agent_builder:
                iteration_state = ctx.state.iteration_state
                iteration_state.iteration_count += 1
                
                deck = await agent_builder.build_initial_deck(request)
                ctx.state.current_deck = deck
                
                return VerifyQualityNode()
            
            # Fallback to heuristic builder
            deck_builder = ctx.deps.get("deck_builder")
            if not deck_builder:
                raise ValueError("No deck builder service found in dependencies")

            iteration_state = ctx.state.iteration_state
            iteration_state.iteration_count += 1

            deck = deck_builder.build_initial_deck(request)
            ctx.state.current_deck = deck

            return VerifyQualityNode()
        except Exception as e:
            ctx.state.errors.append(f"Build initial deck error: {str(e)}")
            return End({"success": False, "error": str(e)})


@dataclass
class RefineDeckNode(BaseNode):
    """
    Refine the deck based on quality feedback.

    Applies suggestions from the verification step to
    improve the deck's quality metrics.
    """

    async def run(self, ctx: GraphRunContext[StateData]) -> Union["VerifyQualityNode", End]:
        """Refine deck using LLM agent reasoning."""
        try:
            request = ctx.state.request
            if not request:
                raise ValueError("No request found in state")

            if ctx.state.current_deck is None:
                raise ValueError("No current deck to refine")

            iteration_state = ctx.state.iteration_state
            iteration_state.iteration_count += 1

            suggestions = (
                ctx.state.latest_quality.suggestions
                if ctx.state.latest_quality
                else []
            )
            
            improvement_plan = (
                ctx.state.latest_quality.improvement_plan
                if ctx.state.latest_quality
                else None
            )
            
            # Try agent-based builder first
            agent_builder = ctx.deps.get("agent_deck_builder")
            if agent_builder:
                deck = await agent_builder.refine_deck(
                    ctx.state.current_deck, suggestions, request, improvement_plan
                )
                ctx.state.current_deck = deck
                return VerifyQualityNode()
            
            # Fallback to heuristic builder
            deck_builder = ctx.deps.get("deck_builder")
            if not deck_builder:
                raise ValueError("No deck builder service found in dependencies")
            
            deck = deck_builder.refine_deck(
                ctx.state.current_deck, suggestions, request, improvement_plan
            )
            ctx.state.current_deck = deck

            return VerifyQualityNode()
        except Exception as e:
            ctx.state.errors.append(f"Refine deck error: {str(e)}")
            return End({"success": False, "error": str(e)})


@dataclass
class VerifyQualityNode(BaseNode):
    """
    Verify and validate the quality of the deck.

    Checks deck quality and determines whether to iterate
    or return the final result.
    """

    async def run(self, ctx: GraphRunContext[StateData]) -> Union["RefineDeckNode", End]:
        """Verify quality and decide whether to iterate or end."""
        try:
            deck = ctx.state.current_deck
            if not deck:
                raise ValueError("No deck found in state")

            # Get quality verifier from dependencies
            quality_verifier: QualityVerifierService = ctx.deps.get("quality_verifier")
            if not quality_verifier:
                raise ValueError("QualityVerifierService not found in dependencies")

            # Verify deck quality with format from request
            request = ctx.state.request
            format_name = request.format if request else "Standard"
            quality_metrics = await quality_verifier.verify_deck(deck, format_name)
            ctx.state.latest_quality = quality_metrics

            # Record this iteration
            iteration_state = ctx.state.iteration_state
            record = IterationRecord(
                iteration=iteration_state.iteration_count,
                deck_snapshot=deck,
                quality_metrics=quality_metrics,
                improvements_applied=quality_metrics.suggestions,
            )
            iteration_state.add_record(record)

            # Decide whether to iterate or end
            should_continue = iteration_state.should_continue(quality_metrics.overall_score)

            if should_continue:
                # Loop back to RefineDeckNode for refinement
                return RefineDeckNode()
            else:
                # End with final results
                return End({
                    "success": True,
                    "deck": deck.model_dump(),
                    "quality_metrics": quality_metrics.model_dump(),
                    "iteration_count": iteration_state.iteration_count,
                    "iteration_history": [
                        {
                            "iteration": r.iteration,
                            "quality_score": r.quality_metrics.overall_score,
                            "issues": r.quality_metrics.issues,
                            "suggestions": r.quality_metrics.suggestions,
                        }
                        for r in iteration_state.history
                    ],
                })
        except Exception as e:
            ctx.state.errors.append(f"Quality verification error: {str(e)}")
            return End({"success": False, "error": str(e)})


class UserModificationNode:
    """
    Node for user-driven deck modifications.

    Handles modifications to existing decks based on user prompts.
    This is a standalone node - not part of the build FSM graph.
    """

    async def execute(
        self,
        mod_request: "DeckModificationRequest",
        agent_deck_builder,
        quality_verifier,
        card_repo
    ) -> Dict[str, Any]:
        """
        Execute user modification.

        Args:
            mod_request: The modification request
            agent_deck_builder: Agent deck builder service
            quality_verifier: Quality verifier service
            card_repo: Card repository

        Returns:
            Dict with modification results
        """
        try:
            deck = mod_request.existing_deck
            user_prompt = mod_request.user_prompt

            # Simple modification using agent's refine_deck method
            # Create a minimal request object for the agent
            from ..models.deck import DeckBuildRequest
            temp_request = DeckBuildRequest(
                format=deck.format,
                colors=deck.colors,
                archetype=deck.archetype or "Midrange",
                quality_threshold=0.7,
                max_iterations=1
            )

            # Use agent to refine based on user prompt
            modified_deck = await agent_deck_builder.refine_deck(
                deck=deck,
                suggestions=[user_prompt],  # User prompt as suggestion
                request=temp_request,
                improvement_plan=None
            )

            # Optional quality check
            quality_after = None
            if mod_request.run_quality_check:
                quality_metrics = await quality_verifier.verify_deck(modified_deck, deck.format)
                quality_after = quality_metrics.overall_score

            return {
                "success": True,
                "deck": modified_deck.model_dump(),
                "modifications": {
                    "summary": f"Applied modification: {user_prompt}",
                    "quality_after": quality_after
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Modification failed: {str(e)}"
            }

