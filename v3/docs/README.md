# MTG Deck Builder - Frontend Architecture Documentation

This directory contains Mermaid diagrams documenting the FastHTML frontend architecture for the MTG Deck Builder application.

## Diagrams

### 1. Simplified State Diagram (`simplified-state-diagram.mmd`) ⭐ **Start Here**

**Purpose**: High-level overview with 6 core states showing the essential user flow.

**States**:
- **Empty**: No deck loaded, fresh start
- **Building**: Chat active, waiting for API response
- **DeckReady**: Deck displayed with save option
- **Saving**: Persisting deck to storage
- **ViewingSaved**: Managing saved decks list
- **EditingDeck**: Editing deck metadata

**Transitions**:
- User sends message → Building → DeckReady
- Save deck → Saving → DeckReady
- View saved decks → ViewingSaved
- Edit/Delete operations in ViewingSaved

**Color Coding**:
- 🟢 Green: Active deck-building states
- 🟠 Orange: Transition/saving state
- 🔵 Blue: Deck management states

### 2. FSM Architecture (`frontend-fsm-architecture.mmd`)

**Purpose**: Documents the Finite State Machine architecture showing all possible states and transitions in the frontend application.

**Key States**:
- **Main Builder**: Initial state with two-column layout
  - `EmptyDeck`: No deck loaded, waiting for user input
  - `DeckLoaded`: Active deck with cards displayed
  - `DeckSaved`: Deck persisted to storage

- **Saved Decks Page**: Management view for saved decks
  - `ViewingDecks`: List of all saved decks
  - `EditingDeck`: Inline name editing mode
  - `UpdatingCategory`: Category selection mode
  - `DeletingDeck`: Confirmation and deletion

**State Transitions**:
- Chat message → Backend API → Deck loaded
- Save deck → Supabase write → Saved state
- View saved → Navigation → Saved decks page
- Load deck → Supabase read → Main builder with deck
- Edit/Delete/Categorize → HTMX partial updates

**Service Integrations**:
- **Current**: Session storage (temporary)
- **Future**: Supabase (persistent storage with auth)
- **Backend**: FastAPI multi-agent system

### 3. Data Flow Diagram (`data-flow-diagram.mmd`)

**Purpose**: Shows how data flows through the system from user interaction to database storage and back.

**Architecture Layers**:

1. **Frontend Layer (FastHTML - Port 5000)**
   - Components: Chat, Deck List, Card, Saved Decks
   - Routes: `/`, `/chat`, `/save_deck`, `/decks`, `/load_deck/*`, `/edit_deck/*`, etc.
   - Session Storage: Current deck, messages, saved decks, context

2. **Backend Layer (FastAPI - Port 8000)**
   - Endpoints: `/api/v1/chat`, `/api/v1/query`, `/api/v1/cards`, `/api/v1/synergy`
   - Services: Multi-Agent Orchestrator, Deck Builder, Vector Store, Card Lookup
   - Data Stores: SQLite (cards), ChromaDB (vectors), Multi-tier cache

3. **Database Layer (Future: Supabase)**
   - Tables: `users`, `saved_decks`, `user_sessions`
   - APIs: Auth, Database CRUD, Realtime subscriptions
   - Features: Authentication, persistent storage, live updates

**Data Flow Examples**:

```
User Sends Chat Message:
User → POST /chat → FastAPI /api/v1/chat → Multi-Agent Orchestrator
→ Deck Builder Service → Vector Store + Card DB → Response JSON
→ Update Session → HTMX Swap → Updated UI

User Saves Deck:
User → POST /save_deck → Session Storage (Current)
                       → Supabase INSERT (Future)
→ Update Deck List → HTMX Swap

User Loads Deck:
User → POST /load_deck/{id} → Session Storage (Current)
                             → Supabase SELECT (Future)
→ Update Current Deck → Navigate to Main Page
```

## Color Coding

Both diagrams use consistent color coding:

- 🟢 **Green** (`#10b981`): Current implementation (session-based)
- 🟠 **Orange** (`#f59e0b`): Future implementation (Supabase)
- 🔵 **Blue** (`#2563eb`): Backend services (FastAPI)
- 🟣 **Purple** (`#8b5cf6`): Data stores (databases, caches)

## Implementation Status

### ✅ Current Implementation (v3)

- [x] Two-column layout (deck list + chat)
- [x] FastHTML components (Card, Chat, Deck List, Saved Decks)
- [x] Session-based storage
- [x] HTMX partial page updates
- [x] Full CRUD for saved decks (in-memory)
- [x] Category management
- [x] Deck loading/saving

### 🔄 In Progress

- [ ] FastAPI backend integration (`/api/chat` endpoint)
- [ ] Multi-agent orchestrator connection
- [ ] Deck builder service integration

### 📋 Planned (Supabase Migration)

#### Database Schema

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Saved decks table
CREATE TABLE saved_decks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  deck_data JSONB NOT NULL,
  category TEXT DEFAULT 'Uncategorized',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- User sessions table (for persistent sessions)
CREATE TABLE user_sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  current_deck JSONB,
  context JSONB,
  messages JSONB[],
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_saved_decks_user_id ON saved_decks(user_id);
CREATE INDEX idx_saved_decks_category ON saved_decks(category);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
```

#### Migration Tasks

- [ ] Set up Supabase project
- [ ] Configure authentication
- [ ] Create database schema
- [ ] Implement Supabase client in frontend
- [ ] Replace session storage with Supabase calls
- [ ] Add user authentication flow
- [ ] Implement realtime deck updates
- [ ] Add Row Level Security (RLS) policies

## Viewing the Diagrams

### Online Viewers

1. **Mermaid Live Editor**: https://mermaid.live/
   - Copy/paste the `.mmd` file contents
   - Export as PNG/SVG

2. **GitHub**:
   - GitHub automatically renders `.mmd` files
   - View directly in the repository

3. **VS Code**:
   - Install "Markdown Preview Mermaid Support" extension
   - Create a `.md` file with mermaid code block
   - Preview with `Ctrl+Shift+V`

### Local Rendering

```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Render to PNG
mmdc -i frontend-fsm-architecture.mmd -o frontend-fsm-architecture.png

# Render to SVG
mmdc -i data-flow-diagram.mmd -o data-flow-diagram.svg
```

## Architecture Decisions

### Why FastHTML?

- Python-native: No JavaScript needed for components
- HTMX integration: Partial page updates without SPA complexity
- Server-side rendering: Better SEO and initial load times
- Type safety: Pydantic integration for data validation
- Component reusability: Clean separation of concerns

### Why Session Storage → Supabase?

**Current (Session Storage)**:
- ✅ Simple implementation
- ✅ No database setup needed
- ✅ Fast development iteration
- ❌ Not persistent (lost on browser close)
- ❌ No multi-device sync
- ❌ No user authentication

**Future (Supabase)**:
- ✅ Persistent storage
- ✅ Multi-device sync
- ✅ Built-in authentication
- ✅ Real-time updates
- ✅ Row-level security
- ✅ Automatic backups
- ✅ PostgreSQL power

### Why FSM Architecture?

- **Predictability**: All states and transitions are explicit
- **Testability**: Easy to unit test state transitions
- **Debuggability**: Clear state tracking for bug reproduction
- **Scalability**: Easy to add new states without breaking existing flows
- **Documentation**: Self-documenting architecture through diagrams

## Related Documentation

- [FastHTML Documentation](https://fastht.ml/)
- [HTMX Documentation](https://htmx.org/)
- [Supabase Documentation](https://supabase.com/docs)
- [Mermaid Documentation](https://mermaid.js.org/)

## Questions?

For questions about the architecture or diagrams, see:
- Architecture discussion: `/v3/README.md`
- Frontend implementation: `/v3/frontend/app.py`
- Component details: `/v3/frontend/components/`
