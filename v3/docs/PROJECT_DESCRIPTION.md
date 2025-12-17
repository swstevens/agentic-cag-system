# Project Description: Agentic MTG Deck Builder

## Application Overview
The **Agentic MTG Deck Builder** is an intelligent web application that helps Magic: The Gathering players build and refine decks. Unlike standard database search tools, it uses an agentic workflow to reason about deck archetypes, strategies, and synergies. Users can interact with the system via natural language allows to build decks from scratch or iteratively modify existing ones.

## AI Techniques Used
1.  **Structured Output (Pydantic AI)**:
    -   We use Pydantic models to constrain LLM responses, forcing the agent to output valid JSON for deck lists, card selections, and improvement plans. This ensures that the application never crashes due to malformed LLM text.
    -   *Example*: The `DeckBuildRequest` and `DeckQualityMetrics` models govern the input/output contract with the LLM.

2.  **Retrieval Augmented Generation (RAG/CAG)**:
    -   **CAG (Cache-Augmented Generation)**: We implement a two-tier retrieval strategy. The system checks a fast LRU cache for card data before falling back to the database.
    -   **Vector Search**: We use embeddings (via `VectorService`) to perform semantic searches (e.g., "find fast red goblins") when exact name matches fail, allowing the agent to discover relevant cards conceptually.

## Key Features
-   **Agentic FSM Workflow**: A "Draft-Verify-Refine" loop that iteratively improves decks based on quality metrics (mana curve, land count) until they meet a threshold.
-   **Optimistic Chat UI**: A responsive FastHTML frontend that provides immediate feedback while the heavy agentic processing happens in the background.
-   **Heuristic + LLM Verification**: Deck quality is assessed by combining hard logic (math-based mana curve analysis) with LLM "vibes" based checks (synergy analysis).
