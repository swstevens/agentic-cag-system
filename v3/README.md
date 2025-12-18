# V3 Architecture - FSM-Based Agentic CAG System

## Overview

V3 is a complete architectural redesign using a **Finite State Machine (FSM)** pattern with Pydantic's graph module. This approach simplifies agentic workflows by constraining operations to well-defined states, resulting in predictable, testable, and maintainable code.

The system leverages **Cache-Augmented Generation (CAG)** patterns for efficient card data retrieval and **LLM-powered agents** for intelligent deck building and quality verification.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip or uv package manager
- OpenAI API key (or compatible LLM provider)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agentic-cag-system/v3

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Initialize the database
python scripts/init_db.py

# Run the backend server
uvicorn api:app --reload --host 0.0.0.0 --port 8000

# In a separate terminal, run the frontend (optional)
cd frontend
python app.py
```

For detailed setup instructions, see [GETTING_STARTED.md](docs/GETTING_STARTED.md).

---

## 📚 Documentation

### Core Documentation

#### Getting Started
- **[GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Installation and setup guide
- **[PROJECT_DESCRIPTION.md](docs/PROJECT_DESCRIPTION.md)** - Project overview and AI features

#### Architecture
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete system architecture (Backend + Frontend)
- **[CODE_ORGANIZATION.md](docs/CODE_ORGANIZATION.md)** - Component diagram showing separation of concerns

#### Diagrams & Workflows
- **[CLASS_DIAGRAM.md](docs/CLASS_DIAGRAM.md)** - UML class diagram of all backend classes
- **[FSM_WORKFLOWS.md](docs/FSM_WORKFLOWS.md)** - Complete FSM state machine workflows and sequence diagrams

### Layer-by-Layer Documentation

- **[01_API_FSM_LAYER.md](docs/layers/01_API_FSM_LAYER.md)** - API endpoints and FSM orchestration
- **[02_SERVICE_LAYER.md](docs/layers/02_SERVICE_LAYER.md)** - Business logic services (AgentBuilder, QualityVerifier, LLM)
- **[03_DATA_ACCESS_CACHING.md](docs/layers/03_DATA_ACCESS_CACHING.md)** - Data persistence and caching layer
- **[04_DOMAIN_MODELS.md](docs/layers/04_DOMAIN_MODELS.md)** - Domain models and data structures

### API Reference

- **[BACKEND_API.md](docs/BACKEND_API.md)** - Complete backend API reference with Python examples
- **[FRONTEND_INTEGRATION.md](docs/FRONTEND_INTEGRATION.md)** - Frontend integration guide with JavaScript examples

### Technical Guides

- **[IMPROVED_EMBEDDINGS.md](docs/IMPROVED_EMBEDDINGS.md)** - Enhanced card embeddings for semantic search

---

## 🎯 Final Project Deliverables (Dec 19)

1. **[PROJECT_DESCRIPTION.md](docs/PROJECT_DESCRIPTION.md)** - Summary of AI features and functionality
2. **[CLASS_DIAGRAM.md](docs/CLASS_DIAGRAM.md)** - UML diagram of main backend classes
3. **[FSM_WORKFLOWS.md](docs/FSM_WORKFLOWS.md)** - Sequence diagrams for deck creation and modification flows
4. **[CODE_ORGANIZATION.md](docs/CODE_ORGANIZATION.md)** - Component diagram showing separation of concerns

---

## 🏗️ Architecture Overview

### FSM States

The system uses a finite state machine with three primary states:

1. **Parse Request** - Parse incoming requests and orchestrate workflow
2. **Build/Modify Deck** - Execute deck building or modification operations
3. **Verify Quality** - Validate and verify deck quality metrics

### System Layers

```
┌─────────────────────────────────────────────────────┐
│ Frontend Layer (FastHTML)                           │
│ - UI Components, HTMX interactions                  │
└────────────────┬────────────────────────────────────┘
                 │ HTTP Requests
┌────────────────▼────────────────────────────────────┐
│ API Layer (FastAPI)                                 │
│ - REST endpoints, Request validation                │
└────────────────┬────────────────────────────────────┘
                 │ Orchestrates
┌────────────────▼────────────────────────────────────┐
│ Core Logic (FSM + Services)                         │
│ - FSM Orchestrator, AgentDeckBuilder                │
│ - QualityVerifier, LLMService                       │
└────────────────┬────────────────────────────────────┘
                 │ Reads/Writes
┌────────────────▼────────────────────────────────────┐
│ Data Layer                                          │
│ - CardRepository (CAG Pattern), DatabaseService     │
│ - VectorService (Embeddings), LRU Cache             │
└─────────────────────────────────────────────────────┘
```

For detailed architecture, see [ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🔑 Key Features

### 1. Agentic Deck Building

- **LLM-Powered Agents** - Uses Pydantic AI agents with tool calling for intelligent card selection
- **Draft-Verify-Refine Loop** - Iterative quality improvement until threshold met
- **Format-Aware** - Supports Standard, Modern, Commander, Legacy, Vintage, Pioneer

### 2. Quality Verification

- **Multi-Metric Analysis** - Mana curve, land ratio, synergy, consistency
- **LLM-Generated Improvements** - Structured improvement plans with specific card suggestions
- **Iteration Tracking** - Full history of quality scores across iterations

### 3. Deck Modifications

- **Natural Language Modifications** - "Add more removal", "Make it more aggressive"
- **Intent Classification** - ADD, REMOVE, REPLACE, OPTIMIZE, STRATEGY_SHIFT
- **Single-Pass Execution** - Fast, responsive modifications without iteration overhead

### 4. Persistence & CRUD

- **Full Deck Management** - Save, load, update, delete decks
- **Metadata Tracking** - Quality scores, creation timestamps, archetype classification
- **Search & Filter** - Find decks by format, archetype, colors

### 5. Cache-Augmented Generation (CAG)

- **LRU Cache Layer** - Fast in-memory card lookups
- **Vector Semantic Search** - Find cards by strategic context ("graveyard synergies")
- **Database Fallback** - SQLite database for complete card catalog

---

## 📁 Project Structure

```
v3/
├── api.py                      # FastAPI backend entry point
├── database/
│   ├── card_repository.py      # CAG pattern card data access
│   ├── database_service.py     # SQLite database operations
│   └── deck_repository.py      # Deck persistence CRUD
├── fsm/
│   ├── orchestrator.py         # FSM orchestrator (routing)
│   └── states.py               # FSM state definitions
├── services/
│   ├── agent_deck_builder_service.py  # LLM-powered deck builder
│   ├── quality_verifier_service.py     # Quality analysis service
│   ├── llm_service.py                  # Generic LLM wrapper
│   ├── vector_service.py               # Embeddings & semantic search
│   └── prompt_builder.py               # System prompt generation
├── models/
│   ├── deck.py                 # Domain models (Deck, Card, etc.)
│   └── format_rules.py         # Format rules and constants
├── frontend/
│   ├── app.py                  # FastHTML frontend server
│   └── components/             # UI components
├── docs/                       # Documentation (see above)
└── tests/                      # Unit and integration tests
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_fsm.py

# Run with coverage
pytest --cov=v3 --cov-report=html
```

---

## 🛠️ Development

### Adding a New Format

1. Update `models/format_rules.py` with format rules
2. Add mana curve standards and land ratios
3. Update `services/prompt_builder.py` with format-specific prompts
4. Test with new deck creation requests

### Modifying FSM Workflow

1. Edit `fsm/states.py` to add/modify states
2. Update `fsm/orchestrator.py` routing logic
3. Document changes in `docs/FSM_WORKFLOWS.md`
4. Add tests in `tests/test_fsm.py`

### Extending the API

1. Add new endpoint in `api.py`
2. Define Pydantic request/response models
3. Update `docs/BACKEND_API.md` with examples
4. Update `docs/FRONTEND_INTEGRATION.md` with frontend usage

---

## 🔍 Key Design Principles

### 1. Separation of Concerns

Each layer has a single, well-defined responsibility:
- **API**: Interface definition, validation, routing
- **FSM**: Workflow orchestration and state management
- **Services**: Business logic (deck building, quality analysis)
- **Data**: Persistence and caching

### 2. Immutability & Predictability

- FSM state transitions are deterministic
- Services are stateless (state managed by FSM)
- All operations return explicit success/error results

### 3. Type Safety

- Pydantic models throughout for runtime validation
- Type hints on all functions
- Validated configs and environment variables

### 4. Testability

- Pure functions for business logic
- Dependency injection for services
- Mocked LLM responses for deterministic tests

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Update documentation
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

---

## 📝 License

[Add your license here]

---

## 🙏 Acknowledgments

- **Pydantic AI** - For the excellent agent framework
- **FastAPI** - For the high-performance web framework
- **Scryfall** - For the comprehensive MTG card database
- **OpenAI** - For GPT-4 and embedding models

---

## 📞 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the [documentation](docs/)
- Review [FSM_WORKFLOWS.md](docs/FSM_WORKFLOWS.md) for workflow questions
- See [BACKEND_API.md](docs/BACKEND_API.md) for API reference

---

**Built with ❤️ for Magic: The Gathering enthusiasts and AI engineers**
