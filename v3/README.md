# V3 Architecture - FSM-Based System

## Overview
V3 is a complete architectural redesign using a Finite State Machine (FSM) pattern with Pydantic's graph module. This approach simplifies the agentic systems by constraining operations to three primary states.

## Final Project Deliverables (Dec 19)
- [**1. Project Description**](docs/PROJECT_DESCRIPTION.md): Summary of AI features and functionality.
- [**2. Class Diagram**](docs/CLASS_DIAGRAM.md): UML diagram of main backend classes.
- [**3. Sequence Diagrams**](docs/SEQUENCE_DIAGRAMS.md): Visualizing New Deck and Modification flows.
- [**4. Code Deployment Diagram**](docs/CODE_ORGANIZATION.md): Component diagram showing separation of concerns.

## Documentation
- [**Getting Started**](docs/GETTING_STARTED.md): Installation and setup guide.
- [**Backend Architecture**](docs/ARCHITECTURE_BACKEND.md): Deep dive into API, FSM, and Services.
- [**Frontend Architecture**](docs/ARCHITECTURE_FRONTEND.md): Overview of FastHTML frontend and components.
- [**Workflows**](docs/WORKFLOWS.md): Detailed FSM and user interaction flows.


### FSM States
1. **Parse Request/Orchestrator**: Parse incoming requests and orchestrate workflow
2. **Query Database**: Execute database queries and retrieve data
3. **Verify Quality**: Validate and verify the quality of results

### Key Modules

- **fsm/**: Finite State Machine implementation using Pydantic graph module
- **database/**: Database layer (reused from v2)
- **schemas/**: Pydantic schemas for data validation (reused from v2)
- **services/**: Business logic services
- **models/**: Data models and domain objects

## Reused Components
- Database layer from v2
- Pydantic schemas from v2
- Card and deck models

## Development Notes
- No complex frameworks like iOrchestrator
- Simplified orchestration through FSM states
- Strong typing with Pydantic throughout
