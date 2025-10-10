from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .config import settings
from .models.card import MTGCard, CardCollection, CardColor, CardType
from .services.cache_service import MultiTierCache
from .services.knowledge_service import KnowledgeService
from .agents.scheduling_agent import SchedulingAgent
from .agents.knowledge_fetch_agent import KnowledgeFetchAgent
from .agents.symbolic_reasoning_agent import SymbolicReasoningAgent
from .controllers.orchestrator import AgentOrchestrator
from .routers.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup: Initialize CAG system
    print("🚀 Starting MTG CAG System...")

    # Initialize cache
    cache = MultiTierCache()
    cache.l1_max_size = settings.cache_l1_max_size
    cache.l2_max_size = settings.cache_l2_max_size
    cache.l3_max_size = settings.cache_l3_max_size

    # Initialize knowledge service
    knowledge_service = KnowledgeService(cache)

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
        knowledge_service=knowledge_service,
        model_name=settings.default_model,
        api_key=settings.openai_api_key
    )
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

    print("✅ MTG CAG System ready!")

    yield

    # Shutdown
    print("👋 Shutting down MTG CAG System...")


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


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MTG CAG System API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "cache_ready": app.state.cache is not None,
        "knowledge_ready": app.state.knowledge_service.kv_cache_ready
    }


if __name__ == "__main__":
    uvicorn.run(
        "mtg_cag_system.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
