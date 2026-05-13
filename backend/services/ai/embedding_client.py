"""
Embedding Client
================
Abstracts embedding generation so the application can use either:
- HTTP/OpenAI-compatible endpoints (llama.cpp server)
- Native FlagEmbedding BGE-M3 embeddings via Python

Configuration (settings.py):
    EMBEDDING_BASE_URL
    EMBEDDING_MODEL
    EMBEDDING_BACKEND
    EMBEDDING_DEVICE
    EMBEDDING_TIMEOUT
    EMBEDDING_RETRY_TIMES
"""

import logging
import time
from typing import Optional, List

import numpy as np
import requests
from django.conf import settings
from core.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


def _normalize_backend(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ('flag', 'flagembedding', 'native'):
        return 'flag'
    if normalized in ('http', 'rest', 'api'):
        return 'http'
    return normalized


class EmbeddingClient:
    """Embedding client supporting HTTP or FlagEmbedding backends."""

    def __init__(
        self,
        api_url: str = None,
        model: str = None,
        backend: str = None,
        device: str = None,
        timeout: int = None,
        retry_times: int = None,
    ):
        self.api_url = api_url or settings.EMBEDDING_BASE_URL
        self.backend = _normalize_backend(backend or getattr(settings, 'EMBEDDING_BACKEND', None))
        self.device = device or getattr(settings, 'EMBEDDING_DEVICE', None)
        self.timeout = timeout or getattr(settings, 'EMBEDDING_TIMEOUT', 60)
        self.retry_times = retry_times or getattr(settings, 'EMBEDDING_RETRY_TIMES', 1)

        if self.backend is None:
            if model and 'bge-m3' in model.lower():
                self.backend = 'flag'
            else:
                self.backend = 'http'

        if model:
            self.model = model
        elif self.backend == 'flag':
            self.model = settings.EMBEDDING_MODEL or 'BAAI/bge-m3'
        else:
            self.model = settings.EMBEDDING_MODEL or settings.LLM_MODEL

        if self.backend == 'http' and not self.api_url:
            raise LLMServiceError('EMBEDDING_BASE_URL is not configured for HTTP embedding backend')

        if self.backend == 'flag':
            self._init_flag_embedding()
        else:
            logger.info(
                f"EmbeddingClient configured for HTTP backend: {self.api_url} model={self.model}"
            )

    def _init_flag_embedding(self):
        try:
            from FlagEmbedding.inference.embedder import BGEM3FlagModel
        except Exception as e:
            logger.error('Failed to import FlagEmbedding for native embeddings', exc_info=True)
            raise LLMServiceError(
                'Native FlagEmbedding backend requested but FlagEmbedding is not available: '
                f'{str(e)}'
            )

        # Default to GPU if available, otherwise CPU
        if self.device is None:
            try:
                import torch
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            except Exception:
                self.device = 'cpu'

        use_fp16 = False
        if self.device and self.device.startswith('cuda'):
            use_fp16 = True

        try:
            self.embedder = BGEM3FlagModel(
                model_name_or_path=self.model,
                devices=self.device,
                normalize_embeddings=True,
                use_fp16=use_fp16,
                use_bf16=False,
            )
            logger.info(
                f'EmbeddingClient configured for FlagEmbedding backend: model={self.model} device={self.device}'
            )
        except Exception as e:
            logger.error('Failed to initialize FlagEmbedding model', exc_info=True)
            raise LLMServiceError(f'Failed to initialize FlagEmbedding model: {str(e)}')

    def create_embedding(self, text: str) -> List[float]:
        if not text:
            raise LLMServiceError('Cannot generate embedding for empty text')

        if self.backend == 'http':
            return self._create_http_embedding(text)
        return self._create_flag_embedding(text)

    def _create_http_embedding(self, text: str) -> List[float]:
        try:
            payload = {
                'model': self.model,
                'input': text,
            }

            response = self._request_with_retry(
                'POST',
                f'{self.api_url}/embeddings',
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                result = response.json()
                if 'data' in result and len(result['data']) > 0:
                    embedding = result['data'][0].get('embedding', [])
                    logger.debug(f'Embedding generated: {len(embedding)} dimensions')
                    return embedding
                raise LLMServiceError('Invalid embedding response format')
            raise LLMServiceError(f'Embedding API error: {response.status_code}')
        except Exception as e:
            logger.error('Embedding generation error (HTTP): %s', str(e), exc_info=True)
            raise LLMServiceError(f'Failed to generate embedding: {str(e)}')

    def _create_flag_embedding(self, text: str) -> List[float]:
        try:
            result = self.embedder.encode(
                [text],
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            if isinstance(result, dict) and 'dense_vecs' in result:
                dense_vecs = np.asarray(result['dense_vecs'])
                if dense_vecs.ndim == 2:
                    dense_vec = dense_vecs[0]
                else:
                    dense_vec = dense_vecs
                embedding = dense_vec.tolist()
                logger.debug(f'Embedding generated (FlagEmbedding): {len(embedding)} dimensions')
                return embedding
            raise LLMServiceError('Invalid FlagEmbedding output format')
        except Exception as e:
            logger.error('Embedding generation error (FlagEmbedding): %s', str(e), exc_info=True)
            raise LLMServiceError(f'Failed to generate embedding: {str(e)}')

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        last_error = None
        for attempt in range(self.retry_times):
            try:
                logger.debug(f'Embedding request ({attempt + 1}/{self.retry_times}): {method} {url}')
                response = requests.request(method, url, **kwargs)
                if response.status_code >= 500:
                    last_error = f'Server error {response.status_code}'
                    if attempt < self.retry_times - 1:
                        time.sleep(2 ** attempt)
                        continue
                return response
            except requests.Timeout as e:
                last_error = f'Timeout after {self.timeout}s: {str(e)}'
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)
                    continue
            except requests.RequestException as e:
                last_error = str(e)
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)
                    continue
        raise LLMServiceError(f'Embedding request failed: {last_error}')
