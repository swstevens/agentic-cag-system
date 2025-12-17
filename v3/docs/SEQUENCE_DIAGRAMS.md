# Sequence Diagrams

## 1. New Deck Creation (FSM Workflow)

This diagram illustrates the user asking for a new deck and the system entering the "Draft-Verify-Refine" loop.

```mermaid
sequenceDiagram
    actor User
    participant Frontend as FastHTML App
    participant API as FastAPI Backend
    participant FSM as FSM Orchestrator
    participant Builder as Agent Builder
    participant Verifier as Quality Verifier
    
    User->>Frontend: "Build a standard zombies deck"
    Frontend->>API: POST /api/chat
    API->>FSM: execute(request)
    
    FSM->>FSM: Parse Request
    
    loop Draft-Verify-Refine
        FSM->>Builder: build_initial_deck()
        Builder-->>FSM: Draft Deck (60 cards)
        
        FSM->>Verifier: verify_quality()
        Verifier-->>FSM: Score: 0.65 (Fail)
        
        FSM->>Builder: refine_deck(suggestions)
        Builder-->>FSM: Updated Deck
        
        FSM->>Verifier: verify_quality()
        Verifier-->>FSM: Score: 0.82 (Pass)
    end
    
    FSM-->>API: Final Deck + Explanation
    API-->>Frontend: JSON Response
    Frontend-->>User: Display Deck Visualizer
```

## 2. Deck Modification (Chat Workflow)

This diagram shows a user modifying an existing deck via the chat interface.

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API
    participant FSM
    participant Agent
    participant DB as Database
    
    User->>Frontend: "Swap Lightning Bolt for Shock"
    note right of User: Deck is currently loaded in session
    
    Frontend->>API: POST /api/modify-deck
    API->>FSM: execute_modification(deck, prompt)
    
    FSM->>Agent: refine_deck(deck, prompt)
    
    Agent->>DB: search_cards("Shock")
    DB-->>Agent: Card Data
    
    Agent->>Agent: Logic: Remove 4x Bolt, Add 4x Shock
    Agent-->>FSM: Modified Deck Object
    
    FSM-->>API: Result
    API-->>Frontend: Updated Deck
    Frontend-->>User: Update UI OOB Swap
```
