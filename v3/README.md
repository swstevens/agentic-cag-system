# V3 Architecture - FSM-Based System

## Overview
V3 is a complete architectural redesign using a Finite State Machine (FSM) pattern with Pydantic's graph module. This approach simplifies the agentic systems by constraining operations to three primary states.

## Architecture

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
