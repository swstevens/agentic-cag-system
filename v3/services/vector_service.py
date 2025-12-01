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
            # Create a rich text representation for embedding
            # Include name, type, text, and keywords for semantic meaning
            text_content = f"""
            Name: {card.name}
            Type: {card.type_line}
            Text: {card.oracle_text or ''}
            Keywords: {', '.join(card.keywords or [])}
            Colors: {', '.join(card.colors or [])}
            """
            
            ids.append(card.id)
            documents.append(text_content.strip())
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
