"""
AI Clients Package
==================
Wrappers for external AI services with retry logic + error handling

Services:
- LlamaClient: LLM inference via llama.cpp OpenAI-compatible API
- QdrantClient: Vector database for embeddings search + management

Configuration (in settings.py):
    LLAMA_API_URL = "http://llama-server:8080/v1"
    LLAMA_MODEL = "Qwen3-4B-Instruct-2507-Q4_K_M"
    LLAMA_TEMPERATURE = 0.7
    LLAMA_MAX_TOKENS = 2048
    
    QDRANT_URL = "http://qdrant:6333"
    QDRANT_COLLECTION = "documents"
    QDRANT_VECTOR_SIZE = 1536
"""

from .llama_client import LlamaClient
from .qdrant_client import QdrantClient

__all__ = [
    'LlamaClient',
    'QdrantClient',
]
