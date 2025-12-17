# Class Diagram

This document provides a comprehensive class diagram of the v3 architecture, broken down into four logical sections for better readability and understanding.

## Part 1: API & FSM Orchestration

This diagram shows the frontend API layer and the FSM (Finite State Machine) orchestration that controls the workflow.

```mermaid
classDiagram
    %% ============================================
    %% API Layer
    %% ============================================
    class FastAPI {
        +FSMOrchestrator orchestrator
        +DeckRepository deck_repository
        +post chat(ChatRequest) ChatResponse
        +post save_deck(SaveDeckRequest) SaveDeckResponse
        +get list_decks(filters) DeckListResponse
        +get get_deck(deck_id) dict
        +put update_deck(deck_id, UpdateDeckRequest) UpdateDeckResponse
        +delete delete_deck(deck_id) DeleteDeckResponse
        +get health() dict
    }

    class ChatRequest {
        +str message
        +dict context
        +dict existing_deck
    }

    class ChatResponse {
        +str message
        +dict deck
        +str error
    }

    class SaveDeckRequest {
        +dict deck
        +str name
        +str description
        +float quality_score
    }

    class SaveDeckResponse {
        +bool success
        +str deck_id
        +str message
        +str error
    }

    class DeckListItem {
        +str id
        +str name
        +str description
        +str format
        +str archetype
        +list colors
        +int total_cards
        +float quality_score
        +str created_at
        +str updated_at
    }

    class DeckListResponse {
        +bool success
        +list decks
        +int total
        +str error
    }

    class UpdateDeckRequest {
        +dict deck
        +str name
        +str description
        +float quality_score
    }

    class UpdateDeckResponse {
        +bool success
        +str message
        +str error
    }

    class DeleteDeckResponse {
        +bool success
        +str message
        +str error
    }

    %% ============================================
    %% FSM Layer (State Machine)
    %% ============================================
    class FSMOrchestrator {
        -DatabaseService db_service
        -VectorService vector_service
        -CardRepository card_repo
        -DeckBuilderService deck_builder
        -LLMService llm_service
        -QualityVerifierService quality_verifier
        -AgentDeckBuilderService agent_deck_builder
        -Graph graph
        +execute(request_data) dict
        -_execute_new_deck(request_data) dict
        -_execute_modification(mod_request) dict
    }

    class StateData {
        +DeckBuildRequest request
        +Deck current_deck
        +IterationState iteration_state
        +DeckQualityMetrics latest_quality
        +list errors
        +DeckModificationRequest modification_request
        +ModificationIntent modification_intent
        +ModificationResult modification_result
    }

    class ParseRequestNode {
        +dict raw_input
        +run(ctx) BuildInitialDeckNode | End
    }

    class BuildInitialDeckNode {
        +run(ctx) VerifyQualityNode | End
    }

    class RefineDeckNode {
        +run(ctx) VerifyQualityNode | End
    }

    class VerifyQualityNode {
        +run(ctx) RefineDeckNode | End
    }

    class UserModificationNode {
        +execute(mod_request, agent_builder, quality_verifier, card_repo) dict
    }

    %% ============================================
    %% Relationships
    %% ============================================

    %% API to FSM
    FastAPI --> FSMOrchestrator : uses
    FastAPI ..> ChatRequest : receives
    FastAPI ..> ChatResponse : returns
    FastAPI ..> SaveDeckRequest : receives
    FastAPI ..> SaveDeckResponse : returns
    FastAPI ..> DeckListResponse : returns
    FastAPI ..> DeckListItem : uses
    FastAPI ..> UpdateDeckRequest : receives
    FastAPI ..> UpdateDeckResponse : returns
    FastAPI ..> DeleteDeckResponse : returns

    %% FSM Orchestration
    FSMOrchestrator --> ParseRequestNode : creates
    FSMOrchestrator --> BuildInitialDeckNode : creates
    FSMOrchestrator --> RefineDeckNode : creates
    FSMOrchestrator --> VerifyQualityNode : creates
    FSMOrchestrator --> UserModificationNode : creates
    FSMOrchestrator ..> StateData : manages

    %% FSM State Transitions
    ParseRequestNode --> BuildInitialDeckNode : transitions to
    BuildInitialDeckNode --> VerifyQualityNode : transitions to
    VerifyQualityNode --> RefineDeckNode : iterates via
    RefineDeckNode --> VerifyQualityNode : transitions to

    %% Styling
    classDef apiStyle fill:#e1f5ff
    classDef fsmStyle fill:#fff4e1
    
    class FastAPI:::apiStyle
    class ChatRequest:::apiStyle
    class ChatResponse:::apiStyle
    class SaveDeckRequest:::apiStyle
    class SaveDeckResponse:::apiStyle
    class DeckListItem:::apiStyle
    class DeckListResponse:::apiStyle
    class UpdateDeckRequest:::apiStyle
    class UpdateDeckResponse:::apiStyle
    class DeleteDeckResponse:::apiStyle
    
    class FSMOrchestrator:::fsmStyle
    class StateData:::fsmStyle
    class ParseRequestNode:::fsmStyle
    class BuildInitialDeckNode:::fsmStyle
    class RefineDeckNode:::fsmStyle
    class VerifyQualityNode:::fsmStyle
    class UserModificationNode:::fsmStyle
```

---

## Part 2: Service Layer

This diagram shows the business logic services that power deck building, quality verification, and AI interactions.

```mermaid
classDiagram
    %% ============================================
    %% Services Layer
    %% ============================================
    class AgentDeckBuilderService {
        -CardRepository card_repo
        -str model_name
        -Agent build_agent
        -Agent refine_agent
        -DeckBuildRequest current_request
        +build_initial_deck(request) Deck
        +refine_deck(deck, suggestions, request, plan) Deck
        -_create_agents_for_format(format_name) void
        -_register_tools() void
        -_execute_construction_plan(plan, request) Deck
        -_execute_refinement_plan(deck, plan, request) Deck
        -_add_filler_cards(deck, needed, request) void
        -_validate_legendary_quantities(deck, format) Deck
    }

    class LLMService {
        -str model_name
        -Agent agent
        +analyze_deck(deck) DeckImprovementPlan
        -_create_agent_for_format(format_name) void
    }

    class QualityVerifierService {
        -LLMService llm_service
        +verify_deck(deck, format) DeckQualityMetrics
        -_analyze_mana_curve(deck) float
        -_analyze_land_ratio(deck, format) float
        -_analyze_synergies(deck) float
        -_analyze_consistency(deck, format) float
        -_identify_issues(deck, metrics) list
        -_generate_suggestions(deck, metrics) list
    }

    class DeckBuilderService {
        -CardRepository card_repo
        +build_initial_deck(request) Deck
        +refine_deck(deck, suggestions, request, plan) Deck
    }

    class VectorService {
        -ChromaClient client
        -OpenAIEmbeddingFunction embedding_fn
        -Collection collection
        -LRUCache cache
        +upsert_cards(cards) int
        +search(query, limit) list
        +count() int
    }

    class PromptBuilder {
        +build_deck_builder_system_prompt(format) str
        +build_refine_agent_system_prompt(format) str
        +build_llm_analyzer_system_prompt(format) str
    }

    %% Lightweight references to other layers
    class FSMOrchestrator {
        <<External>>
    }
    
    class CardRepository {
        <<External>>
    }
    
    class LRUCache {
        <<External>>
    }

    class DeckImprovementPlan {
        <<External>>
    }

    class DeckQualityMetrics {
        <<External>>
    }

    class FormatRules {
        <<External>>
    }

    class DeckConstructionPlan {
        <<External>>
    }

    class RefinementPlan {
        <<External>>
    }

    %% ============================================
    %% Relationships
    %% ============================================

    %% FSM uses services
    FSMOrchestrator --> AgentDeckBuilderService : owns
    FSMOrchestrator --> LLMService : owns
    FSMOrchestrator --> QualityVerifierService : owns
    FSMOrchestrator --> DeckBuilderService : owns
    FSMOrchestrator --> VectorService : owns

    %% Service dependencies
    AgentDeckBuilderService --> CardRepository : uses
    AgentDeckBuilderService ..> PromptBuilder : uses
    AgentDeckBuilderService ..> FormatRules : consults
    AgentDeckBuilderService ..> DeckConstructionPlan : produces
    AgentDeckBuilderService ..> RefinementPlan : produces

    LLMService ..> PromptBuilder : uses
    LLMService ..> DeckImprovementPlan : produces

    QualityVerifierService --> LLMService : uses
    QualityVerifierService ..> FormatRules : consults
    QualityVerifierService ..> DeckQualityMetrics : produces

    DeckBuilderService --> CardRepository : uses

    VectorService --> LRUCache : uses

    %% Styling
    classDef serviceStyle fill:#e8f5e9
    classDef externalStyle fill:#f5f5f5,stroke-dasharray: 5 5
    
    class AgentDeckBuilderService:::serviceStyle
    class LLMService:::serviceStyle
    class QualityVerifierService:::serviceStyle
    class DeckBuilderService:::serviceStyle
    class VectorService:::serviceStyle
    class PromptBuilder:::serviceStyle
    
    class FSMOrchestrator:::externalStyle
    class CardRepository:::externalStyle
    class LRUCache:::externalStyle
    class DeckImprovementPlan:::externalStyle
    class DeckQualityMetrics:::externalStyle
    class FormatRules:::externalStyle
    class DeckConstructionPlan:::externalStyle
    class RefinementPlan:::externalStyle
```

---

## Part 3: Data Access & Caching

This diagram shows the data persistence layer including repositories, database services, and caching infrastructure.

```mermaid
classDiagram
    %% ============================================
    %% Data Access Layer
    %% ============================================
    class CardRepository {
        -DatabaseService db
        -ICache cache
        -VectorService vector_service
        +get_by_name(name) MTGCard
        +get_by_id(id) MTGCard
        +search(filters) list
        +semantic_search(query, filters, limit) list
        +get_cards_by_type(type, limit) list
        +get_cards_by_colors(colors, limit) list
        +get_lands(colors, limit) list
        +preload_popular_cards(names) int
        +get_cache_stats() dict
    }

    class DeckRepository {
        -DatabaseService db
        +save_deck(deck, name, description, quality_score, user_id) str
        +get_deck_by_id(deck_id) dict
        +list_decks(format_filter, archetype_filter, user_id, limit, offset) list
        +update_deck(deck_id, deck, name, description, quality_score) bool
        +delete_deck(deck_id) bool
        +get_deck_count(format_filter, archetype_filter, user_id) int
        -_row_to_dict(row) dict
    }

    class DatabaseService {
        -str db_path
        +get_connection() Connection
        +insert_card(card_data) void
        +bulk_insert_cards(cards) int
        +get_card_by_name(name) dict
        +get_card_by_id(id) dict
        +search_cards(colors, types, cmc_min, cmc_max, rarity, format, text, limit) list
        +get_card_count() int
        -_init_schema() void
        -_row_to_dict(row) dict
    }

    %% ============================================
    %% Caching Layer
    %% ============================================
    class ICache {
        <<interface>>
        +get(key) Any
        +put(key, value) void
        +evict(key) void
        +clear() void
        +get_stats() CacheStats
    }

    class LRUCache {
        -int max_size
        -OrderedDict cache
        -CacheStats stats
        +get(key) Any
        +put(key, value) void
        +evict(key) void
        +clear() void
        +get_stats() CacheStats
    }

    class CacheStats {
        +int hits
        +int misses
        +int evictions
        +int size
        +float hit_rate
    }

    %% Lightweight references to other layers
    class FastAPI {
        <<External>>
    }

    class FSMOrchestrator {
        <<External>>
    }

    class VectorService {
        <<External>>
    }

    class MTGCard {
        <<External>>
    }

    class Deck {
        <<External>>
    }

    class CardSearchFilters {
        <<External>>
    }

    %% ============================================
    %% Relationships
    %% ============================================

    %% API uses repositories
    FastAPI --> DeckRepository : uses

    %% FSM uses repositories
    FSMOrchestrator --> DatabaseService : owns
    FSMOrchestrator --> CardRepository : owns

    %% Repository dependencies
    CardRepository --> DatabaseService : uses
    CardRepository --> ICache : uses
    CardRepository --> VectorService : uses
    CardRepository ..> CardSearchFilters : accepts
    CardRepository ..> MTGCard : returns

    DeckRepository --> DatabaseService : uses
    DeckRepository ..> Deck : stores/retrieves

    DatabaseService ..> MTGCard : stores/retrieves
    DatabaseService ..> Deck : stores/retrieves

    %% Caching
    LRUCache ..|> ICache : implements
    ICache ..> CacheStats : returns
    VectorService --> LRUCache : uses

    %% Styling
    classDef dataAccessStyle fill:#f3e5f5
    classDef cacheStyle fill:#fce4ec
    classDef externalStyle fill:#f5f5f5,stroke-dasharray: 5 5
    
    class CardRepository:::dataAccessStyle
    class DeckRepository:::dataAccessStyle
    class DatabaseService:::dataAccessStyle
    
    class ICache:::cacheStyle
    class LRUCache:::cacheStyle
    class CacheStats:::cacheStyle
    
    class FastAPI:::externalStyle
    class FSMOrchestrator:::externalStyle
    class VectorService:::externalStyle
    class MTGCard:::externalStyle
    class Deck:::externalStyle
    class CardSearchFilters:::externalStyle
```

---

## Part 4: Domain Models

This diagram shows all the domain models (data structures) and their relationships.

```mermaid
classDiagram
    %% ============================================
    %% Core Domain Models
    %% ============================================
    class MTGCard {
        +str id
        +str name
        +str mana_cost
        +float cmc
        +list colors
        +list color_identity
        +str type_line
        +list types
        +list subtypes
        +str oracle_text
        +str power
        +str toughness
        +list keywords
        +dict legalities
        +float price_usd
    }

    class DeckCard {
        +MTGCard card
        +int quantity
    }

    class Deck {
        +list cards
        +str format
        +str archetype
        +list colors
        +int total_cards
        +calculate_totals() void
        +get_lands() list
        +get_nonlands() list
        +get_cards_by_cmc(cmc) list
    }

    class DeckBuildRequest {
        +str format
        +list colors
        +str archetype
        +str strategy
        +float budget
        +float quality_threshold
        +int max_iterations
        +int deck_size
    }

    %% ============================================
    %% Quality & Improvement Models
    %% ============================================
    class DeckQualityMetrics {
        +float mana_curve_score
        +float land_ratio_score
        +float synergy_score
        +float consistency_score
        +float overall_score
        +list issues
        +list suggestions
        +DeckImprovementPlan improvement_plan
        +calculate_overall() void
    }

    class DeckImprovementPlan {
        +list removals
        +list additions
        +str analysis
    }

    class CardRemoval {
        +str card_name
        +str reason
        +int quantity
    }

    class CardSuggestion {
        +str card_name
        +str reason
        +int quantity
    }

    %% ============================================
    %% Iteration & State Models
    %% ============================================
    class IterationState {
        +int iteration_count
        +int max_iterations
        +float quality_threshold
        +list history
        +should_continue(quality) bool
        +add_record(record) void
    }

    class IterationRecord {
        +int iteration
        +Deck deck_snapshot
        +DeckQualityMetrics quality_metrics
        +list improvements_applied
        +datetime timestamp
    }

    class StateData {
        +DeckBuildRequest request
        +Deck current_deck
        +IterationState iteration_state
        +DeckQualityMetrics latest_quality
        +list errors
        +DeckModificationRequest modification_request
        +ModificationIntent modification_intent
        +ModificationResult modification_result
    }

    %% ============================================
    %% Modification Models
    %% ============================================
    class DeckModificationRequest {
        +Deck existing_deck
        +str user_prompt
        +bool run_quality_check
        +int max_changes
        +bool strict_validation
    }

    class ModificationIntent {
        +str intent_type
        +str description
        +list card_changes
        +list constraints
        +float confidence
    }

    class ModificationPlan {
        +str analysis
        +list additions
        +list removals
        +list replacements
        +str strategy_notes
    }

    class ModificationResult {
        +Deck deck
        +list changes_made
        +float quality_before
        +float quality_after
        +str modification_summary
    }

    class CardChange {
        +str action
        +str card_name
        +int quantity
        +str reason
        +str replacement_for
    }

    %% ============================================
    %% Search & Rules Models
    %% ============================================
    class CardSearchFilters {
        +list colors
        +list types
        +float cmc_min
        +float cmc_max
        +str rarity
        +str format_legal
        +str text_query
        +int limit
    }

    class FormatRules {
        <<static>>
        +dict FORMATS
        +dict MANA_CURVE_STANDARDS
        +dict LAND_RATIO_STANDARDS
        +dict ARCHETYPE_LAND_COUNTS
        +get_rules(format) dict
        +get_deck_size(format) int
        +get_copy_limit(format) int
        +is_singleton(format) bool
        +get_legendary_max(format) int
        +get_land_count(format, archetype) int
        +get_land_ratio(format) float
        +get_mana_curve_standards(format) dict
    }

    %% ============================================
    %% Agent Planning Models
    %% ============================================
    class DeckConstructionPlan {
        +str strategy
        +list card_selections
    }

    class CardSelection {
        +str card_name
        +int quantity
        +str reasoning
    }

    class RefinementPlan {
        +str analysis
        +list actions
    }

    class RefinementAction {
        +str type
        +str card_name
        +int quantity
        +str reasoning
    }

    %% ============================================
    %% Relationships
    %% ============================================

    %% Core deck composition
    Deck *-- DeckCard : contains
    DeckCard *-- MTGCard : wraps

    %% Quality metrics
    DeckQualityMetrics *-- DeckImprovementPlan : contains
    DeckImprovementPlan *-- CardRemoval : contains
    DeckImprovementPlan *-- CardSuggestion : contains

    %% Iteration tracking
    IterationState *-- IterationRecord : contains
    IterationRecord *-- Deck : snapshots
    IterationRecord *-- DeckQualityMetrics : tracks

    %% State management
    StateData *-- DeckBuildRequest : contains
    StateData *-- Deck : tracks
    StateData *-- IterationState : manages
    StateData *-- DeckQualityMetrics : holds
    StateData *-- DeckModificationRequest : contains
    StateData *-- ModificationIntent : contains
    StateData *-- ModificationResult : contains

    %% Modification workflow
    DeckModificationRequest *-- Deck : modifies
    ModificationPlan *-- CardChange : contains
    ModificationResult *-- Deck : produces

    %% Agent planning
    DeckConstructionPlan *-- CardSelection : contains
    RefinementPlan *-- RefinementAction : contains

    %% Styling
    classDef modelStyle fill:#fff9c4
    
    class MTGCard:::modelStyle
    class DeckCard:::modelStyle
    class Deck:::modelStyle
    class DeckBuildRequest:::modelStyle
    class DeckQualityMetrics:::modelStyle
    class DeckImprovementPlan:::modelStyle
    class CardRemoval:::modelStyle
    class CardSuggestion:::modelStyle
    class IterationState:::modelStyle
    class IterationRecord:::modelStyle
    class DeckModificationRequest:::modelStyle
    class ModificationIntent:::modelStyle
    class ModificationPlan:::modelStyle
    class ModificationResult:::modelStyle
    class CardChange:::modelStyle
    class CardSearchFilters:::modelStyle
    class FormatRules:::modelStyle
    class DeckConstructionPlan:::modelStyle
    class CardSelection:::modelStyle
    class RefinementPlan:::modelStyle
    class RefinementAction:::modelStyle
    class StateData:::modelStyle
```
