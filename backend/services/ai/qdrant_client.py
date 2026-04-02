"""
Qdrant Client
=============
Vector database client for embedding storage + search

Features:
- Store embeddings in Qdrant collection
- Search similar embeddings (semantic search)
- Delete embeddings
- Batch operations
- Error handling + retry logic

Configuration (from settings.py):
    QDRANT_URL = "http://qdrant:6333"
    QDRANT_COLLECTION = "documents"
    QDRANT_VECTOR_SIZE = 1536
    QDRANT_SIMILARITY_THRESHOLD = 0.7

Collection schema:
    - name: "documents"
    - vector_size: 1536 (Qwen model output)
    - similarity: Cosine
    - payload: {chunk_id, chunk_text, metadata}

Usage:
    client = QdrantClient()
    
    # Store embedding
    vector_id = client.add_embedding(
        chunk_id=123,
        embedding=[0.1, -0.2, ..., 0.5],
        payload={"text": "...", "document_id": 1}
    )
    
    # Search similar
    results = client.search_similar(
        embedding=[0.1, -0.2, ..., 0.5],
        limit=5,
        score_threshold=0.7
    )
    # Returns: [(vector_id, score, payload), ...]
    
    # Delete
    client.delete_embedding(vector_id)
"""

import logging
import time
import json
import requests
import uuid
from typing import List, Dict, Tuple, Optional, Any, Generator
from django.conf import settings
from core.exceptions import VectorDatabaseError

logger = logging.getLogger(__name__)


class QdrantClient:
    """
    Qdrant vector database client
    
    Wraps HTTP API with:
    - Retry logic
    - Error handling
    - Logging
    - Batch operations
    """
    
    def __init__(
        self,
        url: str = None,
        collection: str = None,
        vector_size: int = None,
        timeout: int = None,
        retry_times: int = None,
    ):
        """
        Initialize Qdrant client
        
        Args:
            url: Qdrant API URL (default from settings.QDRANT_URL)
            collection: Collection name (default from settings.QDRANT_COLLECTION)
            vector_size: Vector dimension (default from settings.QDRANT_VECTOR_SIZE)
            timeout: Request timeout in seconds (default 30)
            retry_times: Number of retries (default 3)
        """
        self.url = url or settings.QDRANT_URL
        self.collection = collection or getattr(settings, 'QDRANT_COLLECTION', 'documents')
        self.vector_size = vector_size or getattr(settings, 'QDRANT_VECTOR_SIZE', 1536)
        self.timeout = timeout or getattr(settings, 'QDRANT_TIMEOUT', 30)
        self.retry_times = retry_times or getattr(settings, 'QDRANT_RETRY_TIMES', 3)
        
        if not self.url:
            raise VectorDatabaseError("QDRANT_URL not configured in settings")
        
        # Ensure collection exists
        self._ensure_collection()
        logger.info(f"QdrantClient initialized: {self.url} collection={self.collection}")
    
    # ============================================================================
    # CORE OPERATIONS
    # ============================================================================
    
    def add_embedding(
        self,
        embedding: List[float],
        chunk_id: int = None,
        payload: Dict[str, Any] = None,
        vector_id: str = None,
    ) -> str:
        """
        Add embedding to collection
        
        Args:
            embedding: Vector list (must match vector_size)
            chunk_id: DocumentChunk ID (for reference)
            payload: Additional metadata dict
            vector_id: Custom vector ID (default: auto UUID)
        
        Returns:
            Vector ID (UUID string)
        
        Raises:
            VectorDatabaseError: If storage fails
        
        Example:
            vector_id = client.add_embedding(
                embedding=[0.1, -0.2, 0.3, ...],
                chunk_id=42,
                payload={"document_id": 1, "text": "..."}
            )
        """
        try:
            # Validate embedding size
            if len(embedding) != self.vector_size:
                raise VectorDatabaseError(
                    f"Embedding size {len(embedding)} != {self.vector_size}"
                )
            
            # Generate vector ID if not provided
            if not vector_id:
                vector_id = str(uuid.uuid4())
            
            # Build point
            point = {
                "id": vector_id,
                "vector": embedding,
                "payload": payload or {}
            }
            
            # If chunk_id provided, add to payload
            if chunk_id:
                point["payload"]["chunk_id"] = chunk_id
            
            # Store
            response = self._request_with_retry(
                "PUT",
                f"{self.url}/collections/{self.collection}/points",
                json={"points": [point]}
            )
            
            if response.status_code == 200:
                logger.debug(f"Embedding stored: {vector_id}")
                return vector_id
            else:
                raise VectorDatabaseError(
                    f"Failed to store embedding: {response.status_code}"
                )
        
        except Exception as e:
            logger.error(f"Error adding embedding: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to add embedding: {str(e)}")
    
    def batch_add_embeddings(
        self,
        embeddings: List[Tuple[List[float], Dict[str, Any]]],
    ) -> List[str]:
        """
        Add multiple embeddings at once
        
        Args:
            embeddings: List of (embedding_vector, payload) tuples
        
        Returns:
            List of vector IDs
        """
        try:
            points = []
            vector_ids = []
            
            for embedding, payload in embeddings:
                if len(embedding) != self.vector_size:
                    raise VectorDatabaseError(f"Invalid embedding size")
                
                vector_id = str(uuid.uuid4())
                vector_ids.append(vector_id)
                
                points.append({
                    "id": vector_id,
                    "vector": embedding,
                    "payload": payload or {}
                })
            
            # Batch store
            response = self._request_with_retry(
                "PUT",
                f"{self.url}/collections/{self.collection}/points",
                json={"points": points}
            )
            
            if response.status_code == 200:
                logger.debug(f"Batch stored {len(vector_ids)} embeddings")
                return vector_ids
            else:
                raise VectorDatabaseError(f"Batch store failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error batch adding: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to batch add embeddings: {str(e)}")
    
    def search_similar(
        self,
        embedding: List[float],
        limit: int = 5,
        score_threshold: float = None,
        filter_payload: Dict[str, Any] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar embeddings
        
        Args:
            embedding: Query vector
            limit: Number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            filter_payload: Filter by payload (e.g., {"document_id": 1})
        
        Returns:
            List of (vector_id, score, payload) tuples sorted by score DESC
        
        Example:
            results = client.search_similar(
                embedding=[0.1, -0.2, 0.3, ...],
                limit=10,
                score_threshold=0.7
            )
            
            for vector_id, score, payload in results:
                print(f"ID: {vector_id}, Score: {score:.3f}")
                print(f"  Chunk ID: {payload.get('chunk_id')}")
        """
        try:
            if len(embedding) != self.vector_size:
                raise VectorDatabaseError(f"Query vector size mismatch")
            
            # Build search payload
            search_data = {
                "vector": embedding,
                "limit": limit,
                "with_payload": True,
            }
            
            # Add score threshold if provided
            if score_threshold is not None:
                search_data["score_threshold"] = score_threshold
            
            # Add filter if provided
            if filter_payload:
                search_data["filter"] = {
                    "must": [
                        {"key": k, "match": {"value": v}}
                        for k, v in filter_payload.items()
                    ]
                }
            
            # Search
            response = self._request_with_retry(
                "POST",
                f"{self.url}/collections/{self.collection}/points/search",
                json=search_data
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for result in data.get("result", []):
                    vector_id = str(result.get("id"))
                    score = float(result.get("score", 0.0))
                    payload = result.get("payload", {})
                    
                    results.append((vector_id, score, payload))
                
                logger.debug(f"Search returned {len(results)} results")
                return results
            else:
                raise VectorDatabaseError(f"Search failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error searching embeddings: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to search embeddings: {str(e)}")
    
    def delete_embedding(self, vector_id: str) -> bool:
        """
        Delete embedding by ID
        
        Args:
            vector_id: Vector ID to delete
        
        Returns:
            True if deleted
        """
        try:
            response = self._request_with_retry(
                "DELETE",
                f"{self.url}/collections/{self.collection}/points",
                json={"points_selector": {"points": [vector_id]}}
            )
            
            if response.status_code == 200:
                logger.debug(f"Embedding deleted: {vector_id}")
                return True
            else:
                raise VectorDatabaseError(f"Delete failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            return False
    
    def batch_delete_embeddings(self, vector_ids: List[str]) -> int:
        """
        Delete multiple embeddings
        
        Args:
            vector_ids: List of vector IDs to delete
        
        Returns:
            Number deleted
        """
        try:
            response = self._request_with_retry(
                "DELETE",
                f"{self.url}/collections/{self.collection}/points",
                json={"points_selector": {"points": vector_ids}}
            )
            
            if response.status_code == 200:
                logger.debug(f"Batch deleted {len(vector_ids)} embeddings")
                return len(vector_ids)
            else:
                raise VectorDatabaseError(f"Batch delete failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error batch deleting: {str(e)}")
            return 0
    
    def delete_by_filter(self, filter_payload: Dict[str, Any]) -> int:
        """
        Delete embeddings matching filter
        
        Args:
            filter_payload: Filter criteria (e.g., {"document_id": 1})
        
        Returns:
            Number deleted
        
        Example:
            count = client.delete_by_filter({"document_id": 123})
        """
        try:
            # Build filter
            filter_query = {
                "must": [
                    {"key": k, "match": {"value": v}}
                    for k, v in filter_payload.items()
                ]
            }
            
            response = self._request_with_retry(
                "DELETE",
                f"{self.url}/collections/{self.collection}/points",
                json={"filter": filter_query}
            )
            
            if response.status_code == 200:
                logger.debug(f"Delete by filter succeeded")
                return 1  # Qdrant returns status, not count
            else:
                raise VectorDatabaseError(f"Delete by filter failed: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error deleting by filter: {str(e)}")
            return 0
    
    # ============================================================================
    # COLLECTION MANAGEMENT
    # ============================================================================
    
    def _ensure_collection(self):
        """Ensure collection exists, create if needed"""
        try:
            # Check if collection exists
            response = requests.get(
                f"{self.url}/collections/{self.collection}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.debug(f"Collection '{self.collection}' exists")
                return
            
            # Create collection
            logger.info(f"Creating collection '{self.collection}'...")
            
            create_response = requests.put(
                f"{self.url}/collections/{self.collection}",
                json={
                    "vectors": {
                        "size": self.vector_size,
                        "distance": "Cosine"  # Cosine similarity
                    }
                },
                timeout=self.timeout
            )
            
            if create_response.status_code != 200:
                raise VectorDatabaseError(
                    f"Failed to create collection: {create_response.status_code}"
                )
            
            logger.info(f"Collection '{self.collection}' created")
        
        except Exception as e:
            logger.error(f"Error ensuring collection: {str(e)}")
            raise VectorDatabaseError(f"Failed to ensure collection: {str(e)}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            response = requests.get(
                f"{self.url}/collections/{self.collection}",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise VectorDatabaseError(f"Failed to get collection info")
        
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {}
    
    # ============================================================================
    # INTERNAL - RETRY LOGIC
    # ============================================================================
    
    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """
        HTTP request with retry logic
        
        Retry strategy:
        - Exponential backoff: 1s, 2s, 4s
        - Retry on: ConnectionError, Timeout, 500-503
        """
        last_error = None
        
        for attempt in range(self.retry_times):
            try:
                logger.debug(f"Qdrant request ({attempt + 1}/{self.retry_times}): {method} {url}")
                
                # Add timeout if not present
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = self.timeout
                
                response = requests.request(method, url, **kwargs)
                
                # Retry on 5xx errors
                if response.status_code >= 500:
                    last_error = f"Server error {response.status_code}"
                    if attempt < self.retry_times - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Qdrant error, retrying in {wait_time}s: {last_error}")
                        time.sleep(wait_time)
                        continue
                
                return response
            
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = str(e)
                if attempt < self.retry_times - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Connection error, retrying in {wait_time}s: {last_error}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
            
            except Exception as e:
                last_error = str(e)
                raise
        
        raise VectorDatabaseError(
            f"Qdrant API failed after {self.retry_times} retries: {last_error}"
        )
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def health_check(self) -> bool:
        """Check if Qdrant server is healthy"""
        try:
            response = requests.get(f"{self.url}/health", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False
