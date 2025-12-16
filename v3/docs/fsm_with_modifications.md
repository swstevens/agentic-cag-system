# FSM Architecture: Deck Building + User Modifications

## Simplified State Machine Flow

```mermaid
graph TB
    Start([API Request]) --> Router{Request Type}

    %% New Deck Path
    Router -->|New Deck| Parse[Parse Request Node]
    Parse --> Build[Build Initial Deck Node]
    Build --> Verify[Verify Quality Node]
    Verify --> Decision{Quality OK?}
    Decision -->|Yes| End1([Return Deck])
    Decision -->|No & Iterations Left| Refine[Refine Deck Node]
    Refine --> Verify

    %% User Modification Path
    Router -->|Modify Existing| ModNode[User Modification Node]
    ModNode --> End2([Return Modified Deck])

    %% Styling
    style Start fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Router fill:#FF9800,stroke:#E65100,color:#fff
    style Parse fill:#2196F3,stroke:#1565C0,color:#fff
    style Build fill:#2196F3,stroke:#1565C0,color:#fff
    style Verify fill:#2196F3,stroke:#1565C0,color:#fff
    style Refine fill:#2196F3,stroke:#1565C0,color:#fff
    style ModNode fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Decision fill:#FF5722,stroke:#BF360C,color:#fff
    style End1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style End2 fill:#4CAF50,stroke:#2E7D32,color:#fff
```

## User Modification Node - Detailed

```mermaid
graph TD
    Start([Modification Request]) --> Input[Receive Deck + Prompt]
    Input --> Parse[Parse Intent with LLM]

    Parse --> Classify{Intent Type}

    Classify -->|ADD| Add[Add Cards Path]
    Classify -->|REMOVE| Remove[Remove Cards Path]
    Classify -->|REPLACE| Replace[Replace Cards Path]
    Classify -->|OPTIMIZE| Optimize[Optimize Deck Path]

    %% Add Path
    Add --> SearchAdd[Search for Cards]
    SearchAdd --> ExecAdd[Add to Deck]

    %% Remove Path
    Remove --> FindRem[Identify Cards]
    FindRem --> ExecRem[Remove from Deck]

    %% Replace Path
    Replace --> FindRep[Identify Old Cards]
    FindRep --> SearchRep[Search Replacements]
    SearchRep --> ExecRep[Swap Cards]

    %% Optimize Path
    Optimize --> Analyze[Run Quality Analysis]
    Analyze --> Improve[Apply Improvements]

    %% Convergence
    ExecAdd --> Validate
    ExecRem --> Validate
    ExecRep --> Validate
    Improve --> Validate

    Validate[Validate Deck Rules]
    Validate --> Check{Valid?}

    Check -->|Yes| Success([Return Modified Deck])
    Check -->|No| Fix[Auto-Fix Issues]
    Fix --> Success

    %% Styling
    style Start fill:#4CAF50,stroke:#2E7D32,color:#fff
    style Input fill:#2196F3,stroke:#1565C0,color:#fff
    style Parse fill:#FF9800,stroke:#E65100,color:#fff
    style Classify fill:#FF5722,stroke:#BF360C,color:#fff
    style Add fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Remove fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Replace fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Optimize fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style Validate fill:#FF9800,stroke:#E65100,color:#fff
    style Check fill:#FF5722,stroke:#BF360C,color:#fff
    style Success fill:#4CAF50,stroke:#2E7D32,color:#fff
```

## Request Routing Logic

```mermaid
flowchart LR
    Request[Incoming Request] --> HasDeck{Has existing_deck<br/>field?}

    HasDeck -->|No| NewDeck[New Deck Flow]
    HasDeck -->|Yes| HasPrompt{Has modification<br/>prompt?}

    HasPrompt -->|Yes| ModifyDeck[Modification Flow]
    HasPrompt -->|No| Error[Error: No Prompt]

    NewDeck --> ParseNode[Parse Request Node]
    ModifyDeck --> ModNode[User Modification Node]

    style Request fill:#E3F2FD
    style HasDeck fill:#FFF3E0
    style HasPrompt fill:#FFF3E0
    style NewDeck fill:#E8F5E9
    style ModifyDeck fill:#F3E5F5
    style Error fill:#FFEBEE
```

## Complete FSM State Diagram

```mermaid
stateDiagram-v2
    [*] --> Router: API Request

    state Router {
        [*] --> CheckRequest
        CheckRequest --> NewDeck: No existing deck
        CheckRequest --> Modification: Has existing deck
    }

    Router --> ParseRequest: New Deck
    Router --> UserModification: Modify Deck

    state ParseRequest {
        [*] --> ExtractFormat
        ExtractFormat --> ExtractColors
        ExtractColors --> ExtractArchetype
        ExtractArchetype --> CreateRequest
        CreateRequest --> [*]
    }

    ParseRequest --> BuildInitialDeck

    state BuildInitialDeck {
        [*] --> CreateAgents
        CreateAgents --> BuildSpells
        BuildSpells --> AddLands
        AddLands --> ValidateQuantities
        ValidateQuantities --> [*]
    }

    BuildInitialDeck --> VerifyQuality

    state VerifyQuality {
        [*] --> AnalyzeCurve
        AnalyzeCurve --> AnalyzeLands
        AnalyzeLands --> AnalyzeSynergy
        AnalyzeSynergy --> AnalyzeConsistency
        AnalyzeConsistency --> CalculateScore
        CalculateScore --> GenerateSuggestions
        GenerateSuggestions --> [*]
    }

    VerifyQuality --> CheckQuality: Calculate

    state CheckQuality <<choice>>
    CheckQuality --> RefineDeck: Score < Threshold
    CheckQuality --> End: Score OK

    state RefineDeck {
        [*] --> ApplySuggestions
        ApplySuggestions --> SearchBetter
        SearchBetter --> SwapCards
        SwapCards --> AdjustSize
        AdjustSize --> [*]
    }

    RefineDeck --> VerifyQuality: Re-verify

    state UserModification {
        [*] --> ParseIntent
        ParseIntent --> ClassifyIntent
        ClassifyIntent --> ExecuteIntent
        ExecuteIntent --> ValidateDeck
        ValidateDeck --> AutoFix
        AutoFix --> [*]
    }

    UserModification --> End: Modified

    End --> [*]: Return Result
```

## Key Decision Points

```mermaid
graph TD
    A[System Decision Points] --> B[New Deck vs Modification]
    A --> C[Quality Threshold]
    A --> D[Max Iterations]
    A --> E[Modification Intent]
    A --> F[Validation Strategy]

    B --> B1[Has existing_deck field?]
    C --> C1[Current quality < threshold?]
    D --> D1[iterations < max_iterations?]
    E --> E1{What does user want?}
    F --> F1[Deck size correct?]

    E1 --> E2[Add cards]
    E1 --> E3[Remove cards]
    E1 --> E4[Replace cards]
    E1 --> E5[Optimize deck]

    F1 -->|Too small| F2[Add filler]
    F1 -->|Too large| F3[Trim excess]
    F1 -->|Correct| F4[Continue]

    style A fill:#1976D2,color:#fff
    style B fill:#388E3C,color:#fff
    style C fill:#388E3C,color:#fff
    style D fill:#388E3C,color:#fff
    style E fill:#388E3C,color:#fff
    style F fill:#388E3C,color:#fff
```

## Intent Classification Examples

```mermaid
graph LR
    P1["Add more removal"] --> I1[Intent: ADD<br/>Type: Abstract<br/>Category: Removal]
    P2["Remove all 6+ CMC cards"] --> I2[Intent: REMOVE<br/>Type: Conditional<br/>Filter: CMC >= 6]
    P3["Replace Lightning Bolt with Shock"] --> I3[Intent: REPLACE<br/>Type: Specific<br/>Old: Lightning Bolt<br/>New: Shock]
    P4["Make deck more aggressive"] --> I4[Intent: STRATEGY_SHIFT<br/>Type: Abstract<br/>Target: Lower curve]
    P5["Add 4x Counterspell"] --> I5[Intent: ADD<br/>Type: Specific<br/>Exact: Counterspell x4]
    P6["Fix mana curve"] --> I6[Intent: OPTIMIZE<br/>Type: Quality-based<br/>Focus: Curve]

    style P1 fill:#E3F2FD
    style P2 fill:#E3F2FD
    style P3 fill:#E3F2FD
    style P4 fill:#E3F2FD
    style P5 fill:#E3F2FD
    style P6 fill:#E3F2FD

    style I1 fill:#C8E6C9
    style I2 fill:#C8E6C9
    style I3 fill:#C8E6C9
    style I4 fill:#C8E6C9
    style I5 fill:#C8E6C9
    style I6 fill:#C8E6C9
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant O as Orchestrator
    participant M as ModificationNode
    participant L as LLM
    participant R as CardRepository

    U->>F: Request modification
    F->>A: POST /api/modify-deck
    A->>O: Process modification request
    O->>M: Execute UserModificationNode

    M->>L: Parse intent from prompt
    L-->>M: Intent classification

    alt ADD Intent
        M->>R: Search for cards
        R-->>M: Matching cards
        M->>M: Add to deck
    else REMOVE Intent
        M->>M: Identify cards to remove
        M->>M: Remove from deck
    else REPLACE Intent
        M->>R: Search replacements
        R-->>M: Replacement cards
        M->>M: Swap cards
    end

    M->>M: Validate deck rules
    M->>M: Auto-fix if needed
    M-->>O: Modified deck

    O-->>A: Return result
    A-->>F: Modified deck JSON
    F-->>U: Display changes
```

## Comparison: New Deck vs Modification

| Aspect | New Deck Flow | Modification Flow |
|--------|---------------|-------------------|
| **Entry Node** | ParseRequestNode | UserModificationNode |
| **Iterations** | Multiple (with quality checks) | Single pass |
| **Quality Verification** | Always runs | Optional |
| **User Control** | Format + Archetype only | Specific card-level changes |
| **LLM Usage** | Build from scratch | Intent parsing + targeted changes |
| **Speed** | Slower (multiple iterations) | Faster (one-shot) |
| **Output** | New complete deck | Modified existing deck |

---

## Implementation Notes

### Why Separate Node?

1. **Different Concerns**
   - New deck: Quality-driven iteration
   - Modification: User intent fulfillment

2. **Different Validation**
   - New deck: Must meet quality threshold
   - Modification: Must preserve user choices

3. **Different Performance**
   - New deck: Can iterate multiple times
   - Modification: Should be fast, single-pass

4. **Different User Expectations**
   - New deck: "Build me something good"
   - Modification: "Do exactly what I asked"

### Integration Points

1. **Orchestrator** determines routing based on request
2. **Shared Services** (CardRepository, LLM) used by both paths
3. **Validation** logic reused but applied differently
4. **Quality Metrics** optional in modification flow

---

Ready to implement? The architecture keeps the two flows cleanly separated while sharing core services.
