import aiohttp
from typing import List, Dict, Any
from app.logging_utils import ai_logger
import os

class OllamaService:
    def __init__(self):
        # Allow override via ENV, fallback to the fixed IP
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://10.10.20.144:11434")
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3:latest")
        self.embedding_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

    async def generate_response(self, user_prompt: str, system_prompt: str) -> str:
        """Generates a response using local Ollama model."""
        ai_logger.info(f"Generating Ollama response using {self.model_name}")
        url = f"{self.base_url}/api/generate"
        
        prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "")
                    else:
                        ai_logger.error(f"Ollama error: HTTP {response.status}")
                        return "I apologize, but I am currently unable to process your request."
        except Exception as e:
            ai_logger.error(f"Error calling Ollama API: {e}")
            return "Local AI service is currently unreachable."

    async def generate_embeddings(self, text: str) -> List[float]:
        """Generates embeddings for a single piece of text via Ollama."""
        result = await self.generate_embeddings_batch([text])
        return result[0] if result else []

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of texts using Ollama."""
        if not texts: return []
        
        url = f"{self.base_url}/api/embeddings"
        all_embeddings = []
        
        try:
            async with aiohttp.ClientSession() as session:
                for text in texts:
                    payload = {
                        "model": self.embedding_model,
                        "prompt": text
                    }
                    async with session.post(url, json=payload, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "embedding" in data:
                                all_embeddings.append(data["embedding"])
                        else:
                            ai_logger.error(f"Ollama Embeddings API error: HTTP {response.status}")
            return all_embeddings
        except Exception as e:
            ai_logger.error(f"Error generating embeddings with Ollama: {e}")
            return []

ollama_service = OllamaService()
