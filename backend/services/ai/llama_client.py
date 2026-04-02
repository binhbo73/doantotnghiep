"""
Llama Client
============
LLM inference client for llama.cpp server

Features:
- OpenAI-compatible API calls
- Retry logic with exponential backoff
- Error handling + logging
- Timeout management
- Token counting / limits

Configuration (from settings.py):
    LLAMA_API_URL = "http://llama-server:8080/v1"
    LLAMA_MODEL = "Qwen3-4B-Instruct..."
    LLAMA_TEMPERATURE = 0.7
    LLAMA_MAX_TOKENS = 2048
    LLAMA_TOP_P = 0.9
    LLAMA_TIMEOUT = 60 seconds
    LLAMA_RETRY_TIMES = 3

Usage:
    client = LlamaClient()
    
    # Simple completion
    response = client.complete(
        prompt="Summarize this: ...",
        max_tokens=512
    )
    print(response)
    
    # Chat completion
    messages = [
        {"role": "system", "content": "You are helpful assistant"},
        {"role": "user", "content": "What is Python?"}
    ]
    response = client.chat_complete(messages)
    
    # Streaming (for real-time output)
    for chunk in client.complete_stream(prompt="..."):
        print(chunk, end='', flush=True)
"""

import logging
import time
import requests
from typing import List, Dict, Optional, Generator, Any
from django.conf import settings
from core.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


class LlamaClient:
    """
    Llama.cpp OpenAI-compatible API client
    
    Wraps llama-server endpoint with:
    - Retry logic (exponential backoff)
    - Error handling
    - Logging
    - Timeout
    - Token limits
    """
    
    def __init__(
        self,
        api_url: str = None,
        model: str = None,
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        timeout: int = None,
        retry_times: int = None,
    ):
        """
        Initialize Llama client
        
        Args:
            api_url: API endpoint (default from settings.LLAMA_API_URL)
            model: Model name (default from settings.LLAMA_MODEL)
            temperature: Sampling temperature (default 0.7)
            top_p: Top-p sampling (default 0.9)
            max_tokens: Max output tokens (default 2048)
            timeout: Request timeout in seconds (default 60)
            retry_times: Number of retries (default 3)
        """
        self.api_url = api_url or settings.LLAMA_API_URL
        self.model = model or settings.LLAMA_MODEL
        self.temperature = temperature or getattr(settings, 'LLAMA_TEMPERATURE', 0.7)
        self.top_p = top_p or getattr(settings, 'LLAMA_TOP_P', 0.9)
        self.max_tokens = max_tokens or getattr(settings, 'LLAMA_MAX_TOKENS', 2048)
        self.timeout = timeout or getattr(settings, 'LLAMA_TIMEOUT', 60)
        self.retry_times = retry_times or getattr(settings, 'LLAMA_RETRY_TIMES', 3)
        
        # Validate config
        if not self.api_url:
            raise LLMServiceError("LLAMA_API_URL not configured in settings")
        if not self.model:
            raise LLMServiceError("LLAMA_MODEL not configured in settings")
        
        logger.info(f"LlamaClient initialized: {self.api_url} model={self.model}")
    
    # ============================================================================
    # COMPLETION METHODS
    # ============================================================================
    
    def complete(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None,
    ) -> str:
        """
        Simple text completion
        
        Args:
            prompt: Input prompt
            max_tokens: Max output tokens
            temperature: Sampling temperature (0.0-2.0)
            top_p: Top-p sampling (0.0-1.0)
        
        Returns:
            Generated text
        
        Raises:
            LLMServiceError: If API fails
        
        Example:
            client = LlamaClient()
            response = client.complete(
                "Summarize this article: ...",
                max_tokens=256
            )
        """
        try:
            data = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "top_p": top_p or self.top_p,
                "stream": False,
            }
            
            response = self._request_with_retry(
                "POST",
                f"{self.api_url}/completions",
                json=data,
                timeout=self.timeout
            )
            
            # Extract text from response
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    text = result["choices"][0].get("text", "").strip()
                    logger.debug(f"Completion succeeded: {len(text)} chars")
                    return text
                else:
                    raise LLMServiceError("Invalid response format from LLM")
            else:
                raise LLMServiceError(
                    f"LLM API error: {response.status_code} {response.text}"
                )
        
        except requests.Timeout:
            raise LLMServiceError(f"LLM API timeout after {self.timeout}s")
        except Exception as e:
            logger.error(f"Completion error: {str(e)}", exc_info=True)
            raise LLMServiceError(f"Failed to complete: {str(e)}")
    
    def complete_stream(
        self,
        prompt: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> Generator[str, None, None]:
        """
        Stream text completion (real-time output)
        
        Args:
            prompt: Input prompt
            max_tokens: Max tokens
            temperature: Sampling temperature
        
        Yields:
            Text chunks as they arrive
        
        Example:
            client = LlamaClient()
            for chunk in client.complete_stream("Tell me a story..."):
                print(chunk, end='', flush=True)
        """
        try:
            data = {
                "model": self.model,
                "prompt": prompt,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "stream": True,
            }
            
            response = self._request_with_retry(
                "POST",
                f"{self.api_url}/completions",
                json=data,
                timeout=self.timeout,
                stream=True
            )
            
            if response.status_code != 200:
                raise LLMServiceError(
                    f"LLM API error: {response.status_code}"
                )
            
            # Stream response
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data_str = line[6:].strip()
                            if data_str:
                                import json
                                chunk_data = json.loads(data_str)
                                if "choices" in chunk_data:
                                    text = chunk_data["choices"][0].get("text", "")
                                    if text:
                                        yield text
                        except Exception as e:
                            logger.debug(f"Error parsing stream chunk: {str(e)}")
                            continue
        
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            raise LLMServiceError(f"Failed to stream completion: {str(e)}")
    
    # ============================================================================
    # CHAT COMPLETION METHODS
    # ============================================================================
    
    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: str = None,
    ) -> str:
        """
        Chat completion (conversation-based)
        
        Args:
            messages: List of {"role": "user|assistant|system", "content": "..."}
            max_tokens: Max output tokens
            temperature: Sampling temperature
            system_prompt: Optional system prompt prepended
        
        Returns:
            Assistant response
        
        Example:
            messages = [
                {"role": "system", "content": "You are helpful assistant"},
                {"role": "user", "content": "What is RAG?"}
            ]
            response = client.chat_complete(messages)
        """
        try:
            # Prepend system prompt if provided
            if system_prompt:
                messages = [
                    {"role": "system", "content": system_prompt}
                ] + messages
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "stream": False,
            }
            
            response = self._request_with_retry(
                "POST",
                f"{self.api_url}/chat/completions",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    text = message.get("content", "").strip()
                    logger.debug(f"Chat completion succeeded: {len(text)} chars")
                    return text
                else:
                    raise LLMServiceError("Invalid response format")
            else:
                raise LLMServiceError(
                    f"LLM API error: {response.status_code}"
                )
        
        except Exception as e:
            logger.error(f"Chat completion error: {str(e)}", exc_info=True)
            raise LLMServiceError(f"Failed to chat complete: {str(e)}")
    
    def chat_complete_stream(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = None,
        temperature: float = None,
    ) -> Generator[str, None, None]:
        """
        Stream chat completion
        
        Args:
            messages: List of message dicts
            max_tokens: Max tokens
            temperature: Sampling temperature
        
        Yields:
            Response text chunks
        """
        try:
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
                "stream": True,
            }
            
            response = self._request_with_retry(
                "POST",
                f"{self.api_url}/chat/completions",
                json=data,
                timeout=self.timeout,
                stream=True
            )
            
            if response.status_code != 200:
                raise LLMServiceError(f"LLM API error: {response.status_code}")
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data_str = line[6:].strip()
                            if data_str and data_str != '[DONE]':
                                import json
                                chunk_data = json.loads(data_str)
                                if "choices" in chunk_data:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    text = delta.get("content", "")
                                    if text:
                                        yield text
                        except Exception:
                            continue
        
        except Exception as e:
            logger.error(f"Chat stream error: {str(e)}", exc_info=True)
            raise LLMServiceError(f"Failed to chat stream: {str(e)}")
    
    def create_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        Uses llama.cpp /embeddings endpoint
        
        Args:
            text: Input text string
            
        Returns:
            List of floats (vector representation)
        """
        try:
            data = {
                "model": self.model,
                "input": text,
            }
            
            response = self._request_with_retry(
                "POST",
                f"{self.api_url}/embeddings",
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if "data" in result and len(result["data"]) > 0:
                    embedding = result["data"][0].get("embedding", [])
                    logger.debug(f"Embedding generated: {len(embedding)} dimensions")
                    return embedding
                else:
                    raise LLMServiceError("Invalid embedding response format")
            else:
                raise LLMServiceError(f"Embedding API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Embedding generation error: {str(e)}")
            raise LLMServiceError(f"Failed to generate embedding: {str(e)}")

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
        - Give up after: retry_times
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            **kwargs: requests kwargs (json, data, headers, etc.)
        
        Returns:
            Response object
        
        Raises:
            LLMServiceError: After all retries exhausted
        """
        last_error = None
        
        for attempt in range(self.retry_times):
            try:
                logger.debug(f"Request to LLM ({attempt + 1}/{self.retry_times}): {method} {url}")
                
                response = requests.request(method, url, **kwargs)
                
                # Retry on 5xx errors
                if response.status_code >= 500:
                    last_error = f"Server error {response.status_code}"
                    if attempt < self.retry_times - 1:
                        wait_time = 2 ** attempt  # 1, 2, 4 seconds
                        logger.warning(f"LLM error, retrying in {wait_time}s: {last_error}")
                        time.sleep(wait_time)
                        continue
                
                # Success
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
        
        # All retries exhausted
        raise LLMServiceError(f"LLM API failed after {self.retry_times} retries: {last_error}")
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def health_check(self) -> bool:
        """
        Check if LLM server is healthy
        
        Returns:
            True if server responding
        """
        try:
            response = requests.get(
                f"{self.api_url}/models",
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get LLM model information
        
        Returns:
            Model info dict
        """
        try:
            response = requests.get(
                f"{self.api_url}/models",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise LLMServiceError(f"Failed to get model info: {response.status_code}")
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {}
