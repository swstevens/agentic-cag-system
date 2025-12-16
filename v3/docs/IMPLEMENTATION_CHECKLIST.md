# Implementation Checklist: User Modification Feature

## Overview
This checklist guides the implementation of the deck modification feature, keeping the new flow cleanly separated from the existing deck creation flow.

---

## Phase 1: Data Models ✅ / 🔲 / ⏳

### 1.1 Create Core Models
- [ ] Create `DeckModificationRequest` in [v3/models/deck.py](v3/models/deck.py)
  ```python
  class DeckModificationRequest(BaseModel):
      existing_deck: Deck
      user_prompt: str
      run_quality_check: bool = False
      max_changes: int = 10
      strict_validation: bool = False
  ```

- [ ] Create `ModificationIntent` model
  ```python
  class ModificationIntent(BaseModel):
      intent_type: str  # ADD, REMOVE, REPLACE, OPTIMIZE, STRATEGY_SHIFT
      description: str
      card_changes: List[CardChange]
      constraints: List[str]
      confidence: float
  ```

- [ ] Create `CardChange` model
  ```python
  class CardChange(BaseModel):
      action: str  # "add", "remove", "replace"
      card_name: str
      quantity: int
      reason: str
      replacement_for: Optional[str] = None
  ```

- [ ] Create `ModificationPlan` model
  ```python
  class ModificationPlan(BaseModel):
      analysis: str
      additions: List[CardChange]
      removals: List[CardChange]
      replacements: List[CardChange]
      strategy_notes: str
  ```

- [ ] Create `ModificationResult` model
  ```python
  class ModificationResult(BaseModel):
      deck: Deck
      changes_made: List[str]
      quality_before: Optional[float]
      quality_after: Optional[float]
      modification_summary: str
  ```

**Files to Modify:**
- `v3/models/deck.py` (add new models)

**Verification:**
```python
# Test imports
from v3.models.deck import (
    DeckModificationRequest,
    ModificationIntent,
    CardChange,
    ModificationPlan,
    ModificationResult
)
```

---

## Phase 2: Intent Parser Service 🔲

### 2.1 Create Intent Parser
- [ ] Create `v3/services/intent_parser_service.py`
- [ ] Implement `IntentParserService` class
- [ ] Add LLM-based intent classification
- [ ] Add confidence scoring
- [ ] Add fallback for simple patterns

**Key Methods:**
```python
class IntentParserService:
    async def parse_intent(self, prompt: str, deck: Deck) -> ModificationIntent
    def _classify_intent_type(self, prompt: str) -> str
    def _extract_card_names(self, prompt: str) -> List[str]
    def _extract_constraints(self, prompt: str) -> List[str]
    def _calculate_confidence(self, intent: ModificationIntent) -> float
```

**Example System Prompt:**
```python
"""You are an expert at parsing user intents for Magic: The Gathering deck modifications.

Given a user prompt, classify the intent and extract relevant information:

Intent Types:
- ADD: User wants to add cards
- REMOVE: User wants to remove cards
- REPLACE: User wants to swap specific cards
- OPTIMIZE: User wants to improve deck quality
- STRATEGY_SHIFT: User wants to change deck strategy

Provide structured output with:
1. Intent type
2. Specific cards mentioned (if any)
3. Card types/categories (if abstract)
4. Constraints (budget, CMC limits, etc.)
5. Confidence level (0-1)
"""
```

### 2.2 Add Dynamic Prompts for Intent Parser
- [ ] Add `build_intent_parser_prompt()` to PromptBuilder
- [ ] Include format-specific context
- [ ] Include deck archetype context

**Files to Create:**
- `v3/services/intent_parser_service.py`

**Files to Modify:**
- `v3/services/prompt_builder.py` (add intent parser prompt)

**Verification:**
```python
service = IntentParserService()
intent = await service.parse_intent("Add more removal", deck)
assert intent.intent_type == "ADD"
assert "removal" in intent.description.lower()
```

---

## Phase 3: User Modification Node 🔲

### 3.1 Create FSM Node
- [ ] Create `UserModificationNode` in `v3/fsm/states.py`
- [ ] Implement intent parsing
- [ ] Implement modification execution
- [ ] Add deck validation
- [ ] Add auto-fix for size issues

**Node Structure:**
```python
class UserModificationNode:
    """FSM node for user-driven deck modifications."""

    def __init__(
        self,
        intent_parser: IntentParserService,
        agent_builder: AgentDeckBuilderService,
        quality_verifier: Optional[QualityVerifierService] = None
    ):
        self.intent_parser = intent_parser
        self.agent_builder = agent_builder
        self.quality_verifier = quality_verifier

    async def execute(self, state_data: StateData) -> StateData:
        """Execute user modification."""
        # 1. Parse intent
        intent = await self.intent_parser.parse_intent(
            state_data.modification_request.user_prompt,
            state_data.current_deck
        )

        # 2. Execute modification based on intent
        modified_deck = await self._execute_intent(intent, state_data)

        # 3. Validate deck
        modified_deck = self._validate_and_fix(modified_deck, state_data.request)

        # 4. Optional quality check
        if state_data.modification_request.run_quality_check:
            quality = await self.quality_verifier.verify_deck(
                modified_deck,
                state_data.request.format
            )
            state_data.latest_quality = quality

        # 5. Update state
        state_data.current_deck = modified_deck
        return state_data

    async def _execute_intent(
        self,
        intent: ModificationIntent,
        state_data: StateData
    ) -> Deck:
        """Execute modification based on intent type."""
        if intent.intent_type == "ADD":
            return await self._handle_add(intent, state_data)
        elif intent.intent_type == "REMOVE":
            return self._handle_remove(intent, state_data)
        elif intent.intent_type == "REPLACE":
            return await self._handle_replace(intent, state_data)
        elif intent.intent_type == "OPTIMIZE":
            return await self._handle_optimize(intent, state_data)
        elif intent.intent_type == "STRATEGY_SHIFT":
            return await self._handle_strategy_shift(intent, state_data)
        else:
            raise ValueError(f"Unknown intent type: {intent.intent_type}")
```

### 3.2 Implement Intent Handlers
- [ ] `_handle_add()` - Add cards to deck
- [ ] `_handle_remove()` - Remove cards from deck
- [ ] `_handle_replace()` - Replace specific cards
- [ ] `_handle_optimize()` - Quality-driven optimization
- [ ] `_handle_strategy_shift()` - Strategic changes

### 3.3 Add Validation & Auto-Fix
- [ ] `_validate_and_fix()` - Ensure deck is legal
- [ ] `_fix_deck_size()` - Adjust to correct size
- [ ] `_validate_copy_limits()` - Enforce format rules
- [ ] `_validate_color_identity()` - Check color constraints

**Files to Modify:**
- `v3/fsm/states.py` (add new node)

**Verification:**
```python
node = UserModificationNode(intent_parser, agent_builder)
state = StateData(
    request=build_request,
    current_deck=existing_deck,
    modification_request=mod_request
)
result = await node.execute(state)
assert result.current_deck.total_cards == 60  # Valid deck
```

---

## Phase 4: Orchestrator Integration 🔲

### 4.1 Update StateData Model
- [ ] Add `modification_request: Optional[DeckModificationRequest]` field
- [ ] Add `modification_result: Optional[ModificationResult]` field

**Files to Modify:**
- `v3/fsm/states.py` (update StateData)

### 4.2 Update Orchestrator
- [ ] Add request type detection in `execute()`
- [ ] Route to UserModificationNode for modification requests
- [ ] Keep existing flow for new deck requests

**Implementation:**
```python
class FSMOrchestrator:
    def __init__(self, ...):
        # Existing nodes
        self.parse_node = ParseRequestNode()
        self.build_node = BuildInitialDeckNode(...)
        self.verify_node = VerifyQualityNode(...)
        self.refine_node = RefineDeckNode(...)

        # New node
        self.modification_node = UserModificationNode(
            intent_parser=IntentParserService(),
            agent_builder=self.agent_builder,
            quality_verifier=self.quality_verifier
        )

    async def execute(self, request: Union[DeckBuildRequest, DeckModificationRequest]):
        """Execute appropriate workflow based on request type."""

        # Detect request type
        if isinstance(request, DeckModificationRequest):
            return await self._execute_modification_flow(request)
        else:
            return await self._execute_build_flow(request)

    async def _execute_modification_flow(
        self,
        request: DeckModificationRequest
    ) -> ModificationResult:
        """Execute deck modification workflow."""
        # Initialize state
        state = StateData(
            request=self._create_dummy_build_request(request.existing_deck),
            current_deck=request.existing_deck,
            modification_request=request
        )

        # Execute modification node
        state = await self.modification_node.execute(state)

        # Build result
        result = ModificationResult(
            deck=state.current_deck,
            changes_made=state.changes_made or [],
            quality_before=state.quality_before,
            quality_after=state.latest_quality.overall_score if state.latest_quality else None,
            modification_summary=self._generate_summary(state)
        )

        return result

    async def _execute_build_flow(self, request: DeckBuildRequest) -> Deck:
        """Execute deck build workflow (existing logic)."""
        # ... existing implementation ...
```

**Files to Modify:**
- `v3/fsm/orchestrator.py`

**Verification:**
```python
# Test modification flow
mod_request = DeckModificationRequest(
    existing_deck=deck,
    user_prompt="Add more removal"
)
result = await orchestrator.execute(mod_request)
assert isinstance(result, ModificationResult)

# Test build flow still works
build_request = DeckBuildRequest(...)
deck = await orchestrator.execute(build_request)
assert isinstance(deck, Deck)
```

---

## Phase 5: API Endpoint 🔲

### 5.1 Create Endpoint
- [ ] Add `/api/modify-deck` POST endpoint in `v3/api.py`
- [ ] Add request validation
- [ ] Add error handling
- [ ] Add response formatting

**Implementation:**
```python
@app.post("/api/modify-deck")
async def modify_deck(request: dict):
    """Modify an existing deck based on user prompt."""
    try:
        # Validate request
        if "existing_deck" not in request:
            raise HTTPException(400, "Missing existing_deck")
        if "modification" not in request:
            raise HTTPException(400, "Missing modification")

        # Parse existing deck
        existing_deck = Deck.model_validate(request["existing_deck"])

        # Create modification request
        mod_request = DeckModificationRequest(
            existing_deck=existing_deck,
            user_prompt=request["modification"]["user_prompt"],
            run_quality_check=request["modification"].get("run_quality_check", False),
            max_changes=request["modification"].get("max_changes", 10)
        )

        # Execute modification
        result = await orchestrator.execute(mod_request)

        # Format response
        return {
            "success": True,
            "deck": result.deck.model_dump(),
            "modifications": {
                "changes_made": result.changes_made,
                "summary": result.modification_summary,
                "quality_impact": {
                    "before": result.quality_before,
                    "after": result.quality_after
                } if result.quality_before else None
            }
        }

    except Exception as e:
        logger.error(f"Modification failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
```

### 5.2 Update Existing Endpoint (Optional)
- [ ] Update `/api/chat` to handle both flows
- [ ] Add detection logic for modification requests

**Files to Modify:**
- `v3/api.py`

**Verification:**
```bash
curl -X POST http://localhost:8000/api/modify-deck \
  -H "Content-Type: application/json" \
  -d '{
    "existing_deck": {...},
    "modification": {
      "user_prompt": "Add more removal",
      "run_quality_check": false
    }
  }'
```

---

## Phase 6: Frontend Integration 🔲

### 6.1 Update Frontend to Call New Endpoint
- [ ] Add modification button/interface in `v3/frontend/app.py`
- [ ] Add text input for modification prompt
- [ ] Call `/api/modify-deck` endpoint
- [ ] Display changes made
- [ ] Show before/after quality (if enabled)

**Example UI:**
```python
@rt("/modify")
def post_modify_deck(deck_json: str, prompt: str):
    """Handle deck modification request."""
    import json
    import httpx

    deck_data = json.loads(deck_json)

    response = httpx.post(
        "http://localhost:8000/api/modify-deck",
        json={
            "existing_deck": deck_data,
            "modification": {
                "user_prompt": prompt,
                "run_quality_check": True
            }
        }
    )

    result = response.json()

    if result["success"]:
        return Div(
            H3("Deck Modified!"),
            P(result["modifications"]["summary"]),
            Ul(*[Li(change) for change in result["modifications"]["changes_made"]]),
            DeckDisplay(result["deck"])
        )
    else:
        return Div(
            H3("Error"),
            P(result["error"])
        )
```

**Files to Modify:**
- `v3/frontend/app.py`

---

## Phase 7: Testing 🔲

### 7.1 Unit Tests
- [ ] Test intent parsing with various prompts
- [ ] Test modification node handlers
- [ ] Test deck validation logic
- [ ] Test auto-fix mechanisms

### 7.2 Integration Tests
- [ ] Test full modification flow
- [ ] Test error handling
- [ ] Test quality check integration
- [ ] Test both flows don't interfere

### 7.3 End-to-End Tests
- [ ] Test via API
- [ ] Test via frontend
- [ ] Test edge cases (empty deck, invalid cards, etc.)

**Files to Create:**
- `v3/tests/test_intent_parser.py`
- `v3/tests/test_modification_node.py`
- `v3/tests/test_modification_flow.py`

**Example Tests:**
```python
# test_intent_parser.py
async def test_add_intent():
    parser = IntentParserService()
    intent = await parser.parse_intent("Add more removal", deck)
    assert intent.intent_type == "ADD"
    assert any("removal" in change.reason.lower() for change in intent.card_changes)

# test_modification_node.py
async def test_remove_high_cmc():
    node = UserModificationNode(...)
    state = StateData(
        request=build_request,
        current_deck=deck,
        modification_request=DeckModificationRequest(
            existing_deck=deck,
            user_prompt="Remove all cards above 5 CMC"
        )
    )
    result = await node.execute(state)
    assert all(card.card.cmc <= 5 for card in result.current_deck.get_nonlands())
```

---

## Phase 8: Documentation 🔲

- [ ] Update API documentation
- [ ] Add modification examples to README
- [ ] Document intent types
- [ ] Add troubleshooting guide

**Files to Create/Update:**
- `v3/docs/API.md`
- `v3/docs/MODIFICATION_GUIDE.md`
- `v3/README.md`

---

## Implementation Order (Recommended)

1. **Phase 1**: Data Models (foundation)
2. **Phase 2**: Intent Parser (core logic)
3. **Phase 3**: Modification Node (execution)
4. **Phase 4**: Orchestrator Integration (routing)
5. **Phase 5**: API Endpoint (interface)
6. **Phase 7**: Testing (validation)
7. **Phase 6**: Frontend (optional, can be done later)
8. **Phase 8**: Documentation (polish)

---

## Success Criteria

- [ ] Can modify existing deck via API
- [ ] Intent parsing works for common requests
- [ ] Deck validation ensures legal decks
- [ ] Both flows (build + modify) work independently
- [ ] Tests pass with >80% coverage
- [ ] Documentation complete

---

## Estimated Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1 | 1-2 hours | None |
| Phase 2 | 3-4 hours | Phase 1 |
| Phase 3 | 4-6 hours | Phase 1, 2 |
| Phase 4 | 2-3 hours | Phase 3 |
| Phase 5 | 1-2 hours | Phase 4 |
| Phase 6 | 2-3 hours | Phase 5 |
| Phase 7 | 3-4 hours | All phases |
| Phase 8 | 1-2 hours | All phases |
| **Total** | **17-26 hours** | |

---

Ready to start? Begin with Phase 1 (Data Models) to establish the foundation.
