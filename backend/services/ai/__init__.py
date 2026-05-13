"""
AI Clients Package
==================
Wrappers for external AI services with retry logic + error handling

Services:
- LlamaClient: LLM inference via llama.cpp OpenAI-compatible API
- EmbeddingClient: Text embeddings (HTTP or native FlagEmbedding)
- QdrantClient: Vector database for embeddings search + management

Configuration (in settings.py):
    LLAMA_API_URL = "http://llama-server:8080/v1"
    LLAMA_MODEL = "Qwen3-4B-Instruct-2507-Q4_K_M"
    LLAMA_TEMPERATURE = 0.7
    LLAMA_MAX_TOKENS = 2048
    
    EMBEDDING_BASE_URL = "http://llama-server:8080/v1"
    EMBEDDING_MODEL = "Qwen3-4B-Instruct-2507-Q4_K_M" or "BAAI/bge-m3"
    EMBEDDING_BACKEND = "http" or "flag"
    
    QDRANT_URL = "http://qdrant:6333"
    QDRANT_COLLECTION = "documents"
    QDRANT_VECTOR_SIZE = 1536
"""

from .llama_client import LlamaClient
from .qdrant_client import QdrantClient
from .embedding_client import EmbeddingClient

__all__ = [
    'LlamaClient',
    'QdrantClient',
    'EmbeddingClient',
]
