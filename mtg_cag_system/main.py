from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path

from .config import settings
from .models.card import MTGCard, CardCollection, CardColor, CardType
from .services.cache_service import MultiTierCache
from .services.knowledge_service import KnowledgeService
from .services.database_service import DatabaseService
from .services.card_lookup_service import CardLookupService
from .services.vector_store_service import VectorStoreService
from .agents.scheduling_agent import SchedulingAgent
from .agents.knowledge_fetch_agent import KnowledgeFetchAgent
from .agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from .controllers.orchestrator import AgentOrchestrator
from .routers.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Initialize CAG system
    print("[STARTUP] Starting MTG CAG System...")

    # Initialize cache
    cache = MultiTierCache()
    cache.l1_max_size = settings.cache_l1_max_size
    cache.l2_max_size = settings.cache_l2_max_size
    cache.l3_max_size = settings.cache_l3_max_size

    # Initialize database (AtomicCards database)
    db_path = "./data/cards_atomic.db"
    db = None
    vector_store = None
    if os.path.exists(db_path):
        print(f"📀 Loading database: {db_path}")
        db = DatabaseService(db_path)
        db.connect()
        card_count = db.card_count()
        print(f"   Database contains {card_count:,} unique cards")
    else:
        print(f"⚠️  Database not found at {db_path}")
        print(f"   Run 'python scripts/load_atomic_cards.py' to create it")
        print(f"   System will work with limited card data (sample cards only)")

    # Initialize vector store for semantic search
    print("🔮 Initializing vector store...")
    vector_store = VectorStoreService(persist_directory="./data/chroma")
    if vector_store.is_initialized():
        stats = vector_store.get_embedding_stats()
        print(f"   Vector store ready: {stats['total_embeddings']:,} embeddings loaded")
    else:
        print(f"⚠️  Vector embeddings not found. Run 'python scripts/build_embeddings.py' to create them")
        vector_store = None

    # Initialize card lookup service
    card_lookup_service = CardLookupService(database_service=db)
    
    # Initialize knowledge service with database fallback
    knowledge_service = KnowledgeService(cache, database_service=db)

    # Preload cards if configured
    if settings.preload_on_startup:
        print("📚 Preloading card database...")
        # In production, load from MTGJSON
        # For now, create sample data
        sample_cards = [
            MTGCard(
                id="card_001",
                name="Lightning Bolt",
                mana_cost="{R}",
                cmc=1.0,
                colors=[CardColor.RED],
                color_identity=[CardColor.RED],
                type_line="Instant",
                types=[CardType.INSTANT],
                subtypes=[],
                oracle_text="Lightning Bolt deals 3 damage to any target.",
                set_code="LEA",
                rarity="common",
                legalities={"Standard": "not_legal", "Modern": "legal", "Legacy": "legal"},
                keywords=[]
            ),
            # Add more sample cards...
        ]

        collection = CardCollection(
            cards=sample_cards,
            total_count=len(sample_cards),
            format_filter=settings.default_format
        )

        await knowledge_service.preload_knowledge(collection)
        print(f"✅ Preloaded {len(sample_cards)} cards")

    # Initialize agents
    scheduling_agent = SchedulingAgent(
        model_name=settings.default_model,
        api_key=settings.openai_api_key
    )
    knowledge_agent = KnowledgeFetchAgent(
        card_lookup_service=card_lookup_service,
        model_name=settings.default_model,
        api_key=settings.openai_api_key
    )
    # Attach vector store to knowledge agent for synergy lookup
    knowledge_agent.vector_store = vector_store

    symbolic_agent = SymbolicReasoningAgent(
        model_name=settings.default_model,
        api_key=settings.openai_api_key
    )

    # Initialize orchestrator
    orchestrator = AgentOrchestrator(
        scheduling_agent=scheduling_agent,
        knowledge_agent=knowledge_agent,
        symbolic_agent=symbolic_agent,
        cache=cache
    )

    # Store in app state
    app.state.orchestrator = orchestrator
    app.state.cache = cache
    app.state.knowledge_service = knowledge_service
    app.state.database_service = db
    app.state.vector_store = vector_store

    print("✅ MTG CAG System ready!")

    yield

    # Shutdown
    print("👋 Shutting down MTG CAG System...")
    if db:
        db.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Magic: The Gathering deck building assistant using CAG and multi-agent architecture",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cache_ready": app.state.cache is not None,
        "knowledge_ready": app.state.knowledge_service.kv_cache_ready
    }


@app.get("/")
async def root():
    """Serve the chat interface"""
    return FileResponse(str(Path(__file__).parent / 'static/index.html'))


# Mount the static files directory
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "mtg_cag_system.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
