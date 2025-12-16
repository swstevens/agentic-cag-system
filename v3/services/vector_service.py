"""
Vector Service for semantic search using ChromaDB.

Manages card embeddings and provides semantic search capabilities
to augment the standard attribute-based filtering.
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any, Optional
from ..models.deck import MTGCard
from ..caching import LRUCache

class VectorService:
    """
    Service for managing vector embeddings and semantic search.
    
    Uses ChromaDB to store and query card embeddings.
    """
    
    def __init__(self, persist_path: str = "v3/data/chroma_db"):
        """
        Initialize vector service.
        
        Args:
            persist_path: Path to store ChromaDB data
        """
        self.client = chromadb.PersistentClient(path=persist_path)
        
        # Use OpenAI embeddings
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not found. Vector service may not work.")
            
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name="text-embedding-3-small"
        )
        
        self.collection = self.client.get_or_create_collection(
            name="mtg_cards",
            embedding_function=self.embedding_fn
        )
        
        # Initialize cache for query results
        self.cache = LRUCache(max_size=1000)
        
    def upsert_cards(self, cards: List[MTGCard]) -> int:
        """
        Generate embeddings and save cards to vector store.
        
        Args:
            cards: List of cards to index
            
        Returns:
            Number of cards indexed
        """
        if not cards:
            return 0
            
        ids = []
        documents = []
        metadatas = []
        
        for card in cards:
            # Create semantically rich text for embedding that captures:
            # 1. Card identity (name, type, cost)
            # 2. Mechanical function (what it does)
            # 3. Strategic context (how it's used, synergies, anti-synergies)
            # This enables semantic search for concepts like "aggressive threats",
            # "anti-synergy with graveyard strategies", "disrupts combo decks", etc.

            parts = []

            # Basic identity
            parts.append(f"{card.name} - {card.type_line}")

            # Cost and color information
            if card.mana_cost:
                parts.append(f"Costs {card.mana_cost}")
            else:
                parts.append(f"{int(card.cmc)} mana")

            if card.colors:
                color_names = {
                    "W": "white", "U": "blue", "B": "black",
                    "R": "red", "G": "green"
                }
                color_text = " and ".join([color_names.get(c, c) for c in card.colors])
                parts.append(f"{color_text} card")

            # Oracle text (what it does)
            if card.oracle_text:
                parts.append(card.oracle_text)

            # Power/Toughness for creatures
            if card.power and card.toughness:
                parts.append(f"{card.power}/{card.toughness} creature")

            # Loyalty for planeswalkers
            if card.loyalty:
                parts.append(f"Starting loyalty {card.loyalty}")

            # Keywords (strategic indicators)
            if card.keywords:
                keyword_text = ", ".join(card.keywords)
                parts.append(f"Keywords: {keyword_text}")

            # Strategic context based on card characteristics
            strategic_tags = self._generate_strategic_tags(card)
            if strategic_tags:
                parts.append(". ".join(strategic_tags))

            text_content = ". ".join(parts)

            ids.append(card.id)
            documents.append(text_content)
            metadatas.append({
                "name": card.name,
                "cmc": card.cmc,
                "colors": ",".join(card.colors or []),
                "type": card.type_line
            })
            
        # Upsert in batches of 100 to avoid hitting limits
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(cards), batch_size):
            batch_end = min(i + batch_size, len(cards))
            self.collection.upsert(
                ids=ids[i:batch_end],
                documents=documents[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
            total_upserted += (batch_end - i)
            
        return total_upserted
        
    def search(self, query: str, limit: int = 20) -> List[str]:
        """
        Perform semantic search.
        
        Args:
            query: Natural language query
            limit: Maximum results
            
        Returns:
            List of card IDs
        """
        # Check cache first
        cache_key = f"{query}:{limit}"
        cached_results = self.cache.get(cache_key)
        if cached_results:
            return cached_results
            
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        if not results['ids']:
            return []
            
        # Flatten results (query returns list of lists)
        flat_results = results['ids'][0]
        
        # Cache the results
        self.cache.put(cache_key, flat_results)
        
        return flat_results
        
    def count(self) -> int:
        """Get total number of embedded cards."""
        return self.collection.count()

    def _generate_strategic_tags(self, card: MTGCard) -> List[str]:
        """
        Generate strategic context tags for a card based on its characteristics.

        This helps embeddings capture deck-building concepts like:
        - Synergy categories (graveyard, tribal, +1/+1 counters, etc.)
        - Anti-synergy warnings (conflicts with certain strategies)
        - Strategic roles (aggro threat, control finisher, combo piece, etc.)
        - Interaction types (removal, disruption, protection, etc.)

        Args:
            card: Card to analyze

        Returns:
            List of strategic context strings
        """
        tags = []
        oracle_lower = (card.oracle_text or "").lower()
        type_line_lower = card.type_line.lower()
        keywords = [k.lower() for k in (card.keywords or [])]

        # ===== SYNERGY INDICATORS =====

        # Graveyard synergies
        if any(word in oracle_lower for word in ["graveyard", "dies", "when ~ dies", "from your graveyard", "return", "reanimate"]):
            tags.append("Synergy: Graveyard strategies. Works well with self-mill, sacrifice effects, and reanimation")

        # Tribal synergies
        if card.subtypes:
            for subtype in card.subtypes:
                if "Creature" in card.types and subtype not in ["Legendary"]:
                    tags.append(f"Synergy: {subtype} tribal. Benefits from or enables {subtype} tribal strategies")

        # +1/+1 counter synergies
        if "+1/+1 counter" in oracle_lower or "counter on" in oracle_lower:
            tags.append("Synergy: +1/+1 counters. Works with proliferate, counter manipulation, and counters-matter cards")

        # Artifact synergies
        if "Artifact" in card.types or "artifact" in oracle_lower:
            tags.append("Synergy: Artifact strategies. Enables metalcraft, affinity, and artifact-matters effects")

        # Enchantment synergies
        if "Enchantment" in card.types or "enchantment" in oracle_lower:
            tags.append("Synergy: Enchantment strategies. Works with constellation and enchantress effects")

        # Spellslinger synergies
        if any(word in oracle_lower for word in ["instant or sorcery", "cast a spell", "noncreature spell", "whenever you cast"]):
            tags.append("Synergy: Spellslinger decks. Rewards casting instant and sorcery spells")

        # Token synergies
        if "token" in oracle_lower or "create" in oracle_lower:
            tags.append("Synergy: Token strategies. Creates or benefits from token generation")

        # Sacrifice synergies
        if "sacrifice" in oracle_lower:
            tags.append("Synergy: Sacrifice strategies. Either requires sacrifices or rewards sacrificing permanents")

        # Life gain synergies
        if "gain" in oracle_lower and "life" in oracle_lower:
            tags.append("Synergy: Life gain strategies. Triggers or benefits from life gain effects")

        # ===== ANTI-SYNERGY WARNINGS =====

        # Exile-based removal (anti-synergy with graveyard)
        if "exile" in oracle_lower and any(word in oracle_lower for word in ["target", "destroy", "remove"]):
            tags.append("Anti-synergy: Conflicts with graveyard strategies. Exiling prevents graveyard recursion")

        # Graveyard hate
        if "exile" in oracle_lower and "graveyard" in oracle_lower:
            tags.append("Anti-synergy: Graveyard hate. Disrupts graveyard-based strategies - avoid in graveyard decks")

        # Discard effects (anti-synergy with hand-matters)
        if "discard" in oracle_lower and "each player" in oracle_lower:
            tags.append("Anti-synergy: Symmetric discard. Conflicts with strategies that value card advantage")

        # ===== STRATEGIC ROLES =====

        # Tempo and mana efficiency
        if card.cmc == 1:
            if "Creature" in card.types:
                tags.append("Role: Aggressive one-drop. Critical for fast starts in aggro strategies")
            elif "Instant" in card.types or "Sorcery" in card.types:
                tags.append("Role: Efficient interaction. Low-cost spell for early game tempo")

        # Fast threats (aggro)
        if "Creature" in card.types and card.cmc <= 3:
            if "haste" in keywords or "haste" in oracle_lower:
                tags.append("Role: Aggressive threat with immediate impact. Excellent for aggro strategies")
            try:
                if card.power and int(card.power) >= card.cmc:
                    tags.append("Role: Efficient aggressive threat. Good power-to-cost ratio for aggressive decks")
            except (ValueError, TypeError):
                # Skip cards with variable power (e.g., '*')
                pass

        # Evasion (important for aggro/tempo)
        if any(kw in keywords for kw in ["flying", "unblockable", "menace", "trample"]):
            tags.append("Role: Evasive threat. Can push damage through blockers effectively")

        # Control finishers
        if "Creature" in card.types and card.cmc >= 5:
            tags.append("Role: Late-game finisher. Suitable for control decks that stall until big threats")

        # Card advantage engines
        if any(word in oracle_lower for word in ["draw a card", "draw cards", "draw two"]):
            tags.append("Role: Card advantage engine. Helps maintain resources in longer games")

        # Removal spells
        if any(word in oracle_lower for word in ["destroy target", "exile target", "deals damage to target"]):
            if "creature" in oracle_lower:
                tags.append("Role: Creature removal. Answers opposing threats")
            if "planeswalker" in oracle_lower or "any target" in oracle_lower:
                tags.append("Role: Flexible removal. Can target multiple permanent types")

        # Sweepers/Board wipes
        if any(word in oracle_lower for word in ["destroy all", "exile all", "damage to each"]):
            if "creature" in oracle_lower:
                tags.append("Role: Board wipe. Clears multiple threats - essential for control strategies")
                tags.append("Anti-synergy: Avoid in creature-heavy decks. Punishes your own board presence")

        # Ramp (mana acceleration)
        if any(word in oracle_lower for word in ["add", "search your library for a land", "put a land"]):
            if "mana" in oracle_lower or "Land" in type_line_lower:
                tags.append("Role: Mana acceleration. Enables casting expensive spells earlier")

        # Protection/Hexproof
        if any(word in oracle_lower for word in ["hexproof", "shroud", "protection", "indestructible"]):
            tags.append("Role: Protection. Shields important permanents from removal")

        # Disruption (for controlling opponent)
        if "counter target" in oracle_lower:
            tags.append("Role: Counterspell. Disrupts opponent's strategy by countering spells")

        if "discard" in oracle_lower and "target" in oracle_lower:
            tags.append("Role: Hand disruption. Forces opponent to discard, disrupting their gameplan")

        # Combo enablers
        if any(word in oracle_lower for word in ["untap", "infinite", "take an extra turn"]):
            tags.append("Role: Combo enabler. Potential infinite or game-ending combo piece")

        # ===== FORMAT CONSIDERATIONS =====

        # Commander-specific tags
        if "commander" in oracle_lower or card.cmc >= 6:
            tags.append("Format consideration: Well-suited for Commander format with higher CMC tolerance")

        # Aggressive formats
        if card.cmc <= 2 and "Creature" in card.types:
            tags.append("Format consideration: Excellent for aggressive formats like Standard, Modern, and Pioneer")

        return tags
