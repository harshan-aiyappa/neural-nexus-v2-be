import os
from google import genai
from typing import List, Dict, Any
import json
from dotenv import load_dotenv
from app.logging_utils import ai_logger

load_dotenv()

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def extract_scientific_entities(self, text: str) -> Dict[str, Any]:
        """
        Extracts scientific entities and relationships from text using Gemini.
        Strategically designed for cost-efficiency and high precision.
        """
        ai_logger.info(f"Executing Gemini Scientific Extraction using {self.model_name}")
        prompt = f"""
        You are a specialized scientific data extractor for a Knowledge Graph.
        Extract Nodes (Entities) and Relationships (Edges) from the following text.
        
        Rules:
        1. Target Entities: Herbs, Phytoconstituents (Chemicals), Biomarkers, Health Domains, Diseases, Therapeutic Claims.
        2. Target Relationships: CONTAINS, TREATS, INHIBITS, ACTIVATES, ASSOCIATED_WITH.
        3. Output MUST be valid JSON.
        
        Format:
        {{
            "nodes": [{{ "id": "Unique_ID", "label": "Label", "properties": {{ "name": "Name", "type": "Type" }} }}],
            "relationships": [{{ "source": "ID1", "target": "ID2", "type": "TYPE", "properties": {{}} }}]
        }}
        
        Text to process:
        {text}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                }
            )
            ai_logger.info("Gemini Extraction successful")
            return json.loads(response.text)
        except Exception as e:
            ai_logger.error(f"Error during Gemini extraction: {e}")
            return {"nodes": [], "relationships": []}

    async def generate_embeddings(self, text: str) -> List[float]:
        """Generates embeddings for a single piece of text."""
        result = await self.generate_embeddings_batch([text])
        return result[0] if result else []

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of texts using text-embedding-004.
        Complies with Gemini's 100-request limit per batch.
        """
        if not texts: return []
        
        # Gemini embedding batch limit is 100
        GEMINI_BATCH_LIMIT = 100
        all_embeddings = []
        
        try:
            for i in range(0, len(texts), GEMINI_BATCH_LIMIT):
                chunk = texts[i:i + GEMINI_BATCH_LIMIT]
                ai_logger.info(f"Generating embeddings for chunk of {len(chunk)} texts...")
                result = self.client.models.embed_content(
                    model='models/gemini-embedding-001',
                    contents=chunk
                )
                chunk_embeddings = [emb.values for emb in result.embeddings]
                all_embeddings.extend(chunk_embeddings)
            
            return all_embeddings
        except Exception as e:
            ai_logger.error(f"Error generating embeddings batch: {e}")
            return []

    async def generate_response(self, user_prompt: str, system_prompt: str) -> str:
        """Generates a response using Gemini for RAG or Chat."""
        ai_logger.info(f"Generating RAG response using {self.model_name}")
        try:
            combined_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=combined_prompt
            )
            return response.text
        except Exception as e:
            ai_logger.error(f"Error generating Gemini response: {e}")
            return "I apologize, but I am currently unable to process your request."

gemini_service = GeminiService()

# Celery Task Wrapper (Optional)
try:
    from app.core.celery_app import celery_app
    import asyncio

    @celery_app.task(name="tasks.extract_knowledge", bind=True)
    def extract_knowledge_task(self, text: str):
        """Celery task to run the async extraction in a sync wrapper."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(gemini_service.extract_scientific_entities(text))
except (ImportError, Exception):
    extract_knowledge_task = None
