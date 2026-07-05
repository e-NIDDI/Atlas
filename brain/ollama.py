"""Ollama client for Jarvis brain layer."""

import asyncio
import json
from typing import AsyncGenerator, Optional, Dict, Any, List
import httpx
from pydantic import BaseModel, Field

from jarvis.config import config
from jarvis.logger import logger


class OllamaMessage(BaseModel):
    """Ollama message structure."""
    role: str
    content: str


class OllamaRequest(BaseModel):
    """Ollama API request structure."""
    model: str
    messages: List[OllamaMessage]
    stream: bool = True
    options: Dict[str, Any] = Field(default_factory=dict)


class OllamaResponse(BaseModel):
    """Ollama API response structure."""
    model: str
    created_at: str
    message: OllamaMessage
    done: bool


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ) -> None:
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL
            model: Model name to use
        """
        self.base_url = base_url or config.ollama_url
        self.model = model or config.ollama_model
        self.client = httpx.AsyncClient(timeout=120.0)
        logger.info(f"Ollama client initialized - URL: {self.base_url}, Model: {self.model}")
    
    async def check_connection(self) -> bool:
        """
        Check if Ollama is running and accessible.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                logger.info("Ollama connection successful")
                return True
            logger.warning(f"Ollama returned status {response.status_code}")
            return False
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama - is it running?")
            return False
        except Exception as e:
            logger.error(f"Error checking Ollama connection: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """
        List available models.
        
        Returns:
            List of model names
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                logger.info(f"Available models: {models}")
                return models
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    async def chat(
        self,
        messages: List[OllamaMessage],
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Send chat messages to Ollama and stream responses.
        
        Args:
            messages: List of messages
            stream: Whether to stream responses
            
        Yields:
            Response chunks
        """
        request = OllamaRequest(
            model=self.model,
            messages=messages,
            stream=stream
        )
        
        logger.debug(f"Sending chat request with {len(messages)} messages")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=request.model_dump(),
                timeout=120.0
            )
            
            if response.status_code != 200:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                yield f"Error: {error_msg}"
                return
            
            if stream:
                # Stream response
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                full_response += chunk
                                yield chunk
                            
                            if data.get("done", False):
                                logger.debug(f"Chat response complete: {len(full_response)} chars")
                                break
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse stream line: {e}")
                            continue
            else:
                # Non-streaming response
                data = response.json()
                if "message" in data and "content" in data["message"]:
                    content = data["message"]["content"]
                    logger.debug(f"Chat response: {len(content)} chars")
                    yield content
                else:
                    yield "Error: Invalid response from Ollama"
                    
        except httpx.TimeoutException:
            error_msg = "Request to Ollama timed out"
            logger.error(error_msg)
            yield f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error communicating with Ollama: {e}"
            logger.error(error_msg)
            yield f"Error: {error_msg}"
    
    async def chat_complete(
        self,
        messages: List[OllamaMessage]
    ) -> Optional[str]:
        """
        Send chat messages and get complete response.
        
        Args:
            messages: List of messages
            
        Returns:
            Complete response text or None if error
        """
        chunks = []
        async for chunk in self.chat(messages, stream=False):
            chunks.append(chunk)
        
        return "".join(chunks) if chunks else None
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("Ollama client closed")
    
    async def __aenter__(self) -> "OllamaClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


# Global client instance
ollama_client = OllamaClient()