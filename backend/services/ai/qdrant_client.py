"""
Qdrant Client
=============
Vector database client for embedding storage + search

Features:
- Store embeddings in Qdrant collection
- Search similar embeddings (semantic search)
- Asset collection management
- Delete embeddings
- Batch operations
- Error handling + retry logic
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
    """Qdrant vector database client."""

    ASSET_COLLECTION_NAME = "document_assets"

    def __init__(
        self, url: str = None, collection: str = None,
        vector_size: int = None, timeout: int = None, retry_times: int = None,
    ):
        self.url = url or getattr(settings, 'QDRANT_URL', None)
        self.collection = collection or getattr(settings, 'QDRANT_COLLECTION', 'documents')
        self.vector_size = vector_size or getattr(settings, 'QDRANT_VECTOR_SIZE', 1536)
        self.timeout = timeout or getattr(settings, 'QDRANT_TIMEOUT', 30)
        self.retry_times = retry_times or getattr(settings, 'QDRANT_RETRY_TIMES', 3)
        self.hnsw_m = getattr(settings, 'QDRANT_HNSW_M', 16)
        self.hnsw_ef_construction = getattr(settings, 'QDRANT_HNSW_EF_CONSTRUCTION', 256)
        self.search_ef = getattr(settings, 'QDRANT_SEARCH_EF', 128)
        self.full_scan_threshold = getattr(settings, 'QDRANT_FULL_SCAN_THRESHOLD', 100)
        self.quantization = getattr(settings, 'QDRANT_QUANTIZATION', None) or None

        if not self.url:
            raise VectorDatabaseError("QDRANT_URL not configured in settings")

        self._ensure_collection()
        logger.info(f"QdrantClient initialized: {self.url} collection={self.collection}")

    # ============================================================================
    # CORE OPERATIONS
    # ============================================================================

    def add_embedding(
        self, embedding: List[float], chunk_id: int = None,
        payload: Dict[str, Any] = None, vector_id: str = None,
    ) -> str:
        """Add embedding to collection. Returns vector_id."""
        t_start = time.monotonic()
        try:
            if len(embedding) != self.vector_size:
                raise VectorDatabaseError(f"Embedding size mismatch: {len(embedding)} != {self.vector_size}")

            if not vector_id:
                vector_id = str(uuid.uuid4())

            # sanitize payload: convert non-JSON-serializable types like UUID to str
            def _sanitize(obj):
                if isinstance(obj, uuid.UUID):
                    return str(obj)
                if isinstance(obj, dict):
                    return {k: _sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                return obj

            safe_payload = _sanitize(payload or {})
            if chunk_id:
                safe_payload["chunk_id"] = str(chunk_id)

            point = {"id": vector_id, "vector": embedding, "payload": safe_payload}

            response = self._request_with_retry(
                "PUT", f"{self.url}/collections/{self.collection}/points",
                json={"points": [point]}
            )

            if response.status_code == 200:
                logger.info(f"[QDRANT] add_embedding vector_id={vector_id} time={(time.monotonic()-t_start)*1000:.1f}ms")
                return vector_id
            else:
                raise VectorDatabaseError(f"Failed to store embedding: {response.status_code}")
        except Exception as e:
            logger.error(f"Error adding embedding: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to add embedding: {str(e)}")

    def batch_add_embeddings(
        self,
        embeddings: List[Tuple[List[float], Dict[str, Any]]],
    ) -> List[str]:
        """Add multiple embeddings to the main collection."""
        t_start = time.monotonic()
        try:
            points = []
            vector_ids = []
            for embedding, payload in embeddings:
                if len(embedding) != self.vector_size:
                    raise VectorDatabaseError(
                        f"Embedding size mismatch: {len(embedding)} != {self.vector_size}"
                    )
                vector_id = str(uuid.uuid4())
                vector_ids.append(vector_id)
                points.append({
                    "id": vector_id,
                    "vector": embedding,
                    "payload": payload or {},
                })

            if not points:
                return []

            response = self._request_with_retry(
                "PUT", f"{self.url}/collections/{self.collection}/points",
                json={"points": points},
            )
            if response.status_code == 200:
                logger.info(
                    "[QDRANT] batch_add_embeddings count=%s time=%.1fms",
                    len(vector_ids),
                    (time.monotonic() - t_start) * 1000,
                )
                return vector_ids
            raise VectorDatabaseError(f"Batch store failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error batch adding embeddings: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to batch add embeddings: {str(e)}")

    def search_similar(
        self, embedding: List[float], limit: int = 5,
        score_threshold: float = None, filter_payload: Dict[str, Any] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search similar embeddings."""
        t_start = time.monotonic()
        try:
            search_data = {"vector": embedding, "limit": limit, "with_payload": True}
            if score_threshold is not None:
                search_data["score_threshold"] = score_threshold
            if filter_payload:
                must_conditions = []
                for k, v in filter_payload.items():
                    must_conditions.append({"key": k, "match": {"any": v} if isinstance(v, list) else {"value": v}})
                search_data["filter"] = {"must": must_conditions}

            search_data["search_params"] = {"hnsw_ef": self.search_ef}
            response = self._request_with_retry(
                "POST", f"{self.url}/collections/{self.collection}/points/search",
                json=search_data
            )

            if response.status_code == 200:
                results = []
                for r in response.json().get("result", []):
                    results.append((str(r.get("id")), float(r.get("score", 0)), r.get("payload", {})))
                logger.info(f"[QDRANT_SEARCH] results={len(results)} time={(time.monotonic()-t_start)*1000:.1f}ms")
                return results
            else:
                raise VectorDatabaseError(f"Search failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error searching: {str(e)}", exc_info=True)
            raise VectorDatabaseError(f"Failed to search: {str(e)}")

    def delete_embedding(self, vector_id: str) -> bool:
        """Delete embedding by ID."""
        try:
            response = self._request_with_retry(
                "POST", f"{self.url}/collections/{self.collection}/points/delete",
                params={"wait": "true"},
                json={"points": [vector_id]},
            )
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error(f"Error deleting embedding: {str(e)}")
            return False

    def batch_delete_embeddings(self, vector_ids: List[str]) -> int:
        """Delete multiple embeddings from the main collection."""
        if not vector_ids:
            return 0
        try:
            response = self._request_with_retry(
                "POST", f"{self.url}/collections/{self.collection}/points/delete",
                params={"wait": "true"},
                json={"points": vector_ids},
            )
            if response.status_code in (200, 202):
                logger.debug("Batch deleted %s embeddings", len(vector_ids))
                return len(vector_ids)
            raise VectorDatabaseError(f"Batch delete failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error batch deleting embeddings: {str(e)}")
            return 0

    def delete_by_filter(self, filter_payload: Dict[str, Any]) -> int:
        """Delete embeddings matching a payload filter from the main collection."""
        try:
            filter_query = {
                "must": [
                    {"key": key, "match": {"any": value} if isinstance(value, list) else {"value": value}}
                    for key, value in (filter_payload or {}).items()
                ]
            }
            response = self._request_with_retry(
                "POST", f"{self.url}/collections/{self.collection}/points/delete",
                params={"wait": "true"},
                json={"filter": filter_query},
            )
            if response.status_code in (200, 202):
                logger.debug("Delete by filter succeeded: %s", filter_payload)
                return 1
            raise VectorDatabaseError(f"Delete by filter failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error deleting by filter: {str(e)}")
            return 0

    # ============================================================================
    # ASSET COLLECTION (document_assets)
    # ============================================================================

    def _asset_vector_size(self) -> int:
        return int(getattr(settings, 'QDRANT_ASSET_VECTOR_SIZE', self.vector_size))

    def ensure_asset_collection(self) -> str:
        """Create document_assets collection if not exists."""
        try:
            resp = requests.get(f"{self.url}/collections/{self.ASSET_COLLECTION_NAME}", timeout=self.timeout)
            if resp.status_code == 200:
                return self.ASSET_COLLECTION_NAME
        except Exception:
            pass

        logger.info(f"Creating asset collection '{self.ASSET_COLLECTION_NAME}'...")
        resp = requests.put(
            f"{self.url}/collections/{self.ASSET_COLLECTION_NAME}",
            json={"vectors": {"size": self._asset_vector_size(), "distance": "Cosine"}},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise VectorDatabaseError(f"Failed to create asset collection: {resp.status_code}")
        return self.ASSET_COLLECTION_NAME

    def add_asset_embedding(
        self, embedding: List[float], asset_id: str, document_id: str,
        chunk_id: str = None, caption: str = '', page_number: int = None,
        sheet_name: str = None, anchor_cell: str = None, image_path: str = '',
    ) -> str:
        """Add asset caption embedding to document_assets collection."""
        self.ensure_asset_collection()
        expected_size = self._asset_vector_size()
        if len(embedding) != expected_size:
            raise VectorDatabaseError(
                f"Asset embedding size mismatch: {len(embedding)} != {expected_size}"
            )
        vector_id = str(uuid.uuid4())

        payload = {
            'asset_id': str(asset_id), 'document_id': str(document_id),
            'chunk_id': str(chunk_id) if chunk_id else None,
            'caption': caption[:500], 'page_number': page_number,
            'sheet_name': sheet_name, 'anchor_cell': anchor_cell,
            'image_path': image_path, 'asset_type': 'document_asset',
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        resp = requests.put(
            f"{self.url}/collections/{self.ASSET_COLLECTION_NAME}/points",
            json={"points": [{"id": vector_id, "vector": embedding, "payload": payload}]},
            timeout=self.timeout,
        )
        if resp.status_code == 200:
            logger.debug(f"Asset embedding added: asset={asset_id}, vector={vector_id}")
            return vector_id
        raise VectorDatabaseError(f"Failed to add asset embedding: {resp.status_code}")

    def search_assets(
        self, embedding: List[float], limit: int = 5,
        score_threshold: float = 0.5, document_ids: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search assets by embedding. Returns empty list on any error."""
        try:
            self.ensure_asset_collection()
            search_data = {"vector": embedding, "limit": limit, "with_payload": True}
            if score_threshold is not None:
                search_data["score_threshold"] = score_threshold
            if document_ids:
                search_data["filter"] = {"must": [{"key": "document_id", "match": {"any": document_ids}}]}

            resp = requests.post(
                f"{self.url}/collections/{self.ASSET_COLLECTION_NAME}/points/search",
                json=search_data, timeout=self.timeout,
            )
            if resp.status_code != 200:
                logger.warning(f"Asset search HTTP {resp.status_code}: {resp.text[:200]}")
                return []

            assets = []
            for hit in (resp.json() or {}).get("result", []) or []:
                p = hit.get("payload", {}) or {}
                assets.append({
                    'vector_id': str(hit.get("id", "")),
                    'score': float(hit.get("score", 0)),
                    'asset_id': p.get('asset_id'),
                    'document_id': p.get('document_id'),
                    'chunk_id': p.get('chunk_id'),
                    'caption': p.get('caption', ''),
                    'page_number': p.get('page_number'),
                    'sheet_name': p.get('sheet_name'),
                    'anchor_cell': p.get('anchor_cell'),
                    'image_path': p.get('image_path', ''),
                })
            return assets
        except Exception as e:
            logger.warning(f"Asset search failed (non-fatal): {e}")
            return []

    def delete_asset_embeddings(self, document_id: str) -> int:
        """Delete all asset embeddings for a document."""
        try:
            resp = requests.post(
                f"{self.url}/collections/{self.ASSET_COLLECTION_NAME}/points/delete",
                params={"wait": "true"},
                json={"filter": {"must": [{"key": "document_id", "match": {"value": str(document_id)}}]}},
                timeout=self.timeout,
            )
            if resp.status_code in (200, 202):
                logger.info(f"Deleted asset embeddings for document {document_id}")
                return 1
            return 0
        except Exception as e:
            logger.warning(f"Failed to delete asset embeddings: {e}")
            return 0

    def get_collection_info(self) -> Dict[str, Any]:
        """Get main collection metadata and statistics."""
        try:
            response = requests.get(
                f"{self.url}/collections/{self.collection}",
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json()
            raise VectorDatabaseError(f"Failed to get collection info: {response.status_code}")
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            return {}

    # ============================================================================
    # INTERNAL - RETRY LOGIC & COLLECTION
    # ============================================================================

    def _ensure_collection(self):
        """Ensure main collection exists."""
        try:
            response = requests.get(f"{self.url}/collections/{self.collection}", timeout=self.timeout)
            if response.status_code == 200:
                return
        except Exception:
            pass

        logger.info(f"Creating collection '{self.collection}'...")
        create_payload = {
            "vectors": {"size": self.vector_size, "distance": "Cosine",
                         "hnsw_config": {"m": self.hnsw_m, "ef_construct": self.hnsw_ef_construction,
                                         "full_scan_threshold": self.full_scan_threshold}}
        }
        if self.quantization:
            create_payload["vectors"]["quantization_config"] = {"type": self.quantization}

        resp = requests.put(f"{self.url}/collections/{self.collection}", json=create_payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise VectorDatabaseError(f"Failed to create collection: {resp.status_code}")
        logger.info(f"Collection '{self.collection}' created")

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """HTTP request with retry logic."""
        last_error = None
        for attempt in range(self.retry_times):
            try:
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = self.timeout
                response = requests.request(method, url, **kwargs)
                if response.status_code >= 500 and attempt < self.retry_times - 1:
                    last_error = f"Server error {response.status_code}"
                    time.sleep(2 ** attempt)
                    continue
                return response
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = str(e)
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise VectorDatabaseError(f"Qdrant API failed after {self.retry_times} retries: {last_error}")

    def health_check(self) -> bool:
        """Check if Qdrant server is healthy."""
        try:
            response = requests.get(f"{self.url}/health", timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Qdrant health check failed: {str(e)}")
            return False
