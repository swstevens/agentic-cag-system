# Code Organization Diagram

This diagram verifies the "Separation of Concerns" requirement.

```mermaid
graph TB
    subgraph Frontend [Frontend Layer]
        direction TB
        App["app.py<br>(FastHTML Entry)"]
        Comps["components/<br>(UI Widgets)"]
        Static["static/<br>(CSS/Assets)"]
    end

    subgraph API [API Layer]
        Router["api.py<br>(FastAPI Router)"]
        Schemas["schemas/<br>(Pydantic Models)"]
    end

    subgraph Core [Core Logic]
        FSM["fsm/<br>(State Machine)"]
        Services["services/<br>(Business Logic)"]
        Agents["services/agents<br>(LLM Integration)"]
    end

    subgraph Data [Data Layer]
        Repo["database/card_repository.py<br>(CAG Pattern)"]
        DBService["database/database_service.py<br>(SQL Ops)"]
        Vector["services/vector_service.py<br>(Embeddings)"]
    end

    %% Dependencies
    Frontend -->|HTTP Requests| API
    API -->|Orchestrates| Core
    Core -->|Reads/Writes| Data

    %% Separation of Concerns Logic
    style Frontend fill:#e1f5fe,stroke:#01579b
    style API fill:#fff3e0,stroke:#e65100
    style Core fill:#e8f5e9,stroke:#1b5e20
    style Data fill:#f3e5f5,stroke:#4a148c
```

## Module Responsibilities

1.  **Frontend (`frontend/`)**: Pure UI rendering. No database access. Uses HTMX for interactions.
2.  **API (`api.py`)**: Interface definition. Handles validation and routing. No business logic.
3.  **Core (`fsm/`, `services/`)**: Application logic and AI agents.
4.  **Data (`database/`)**: Persistence layer. Hides SQL/Vector/Cache details from the core.
