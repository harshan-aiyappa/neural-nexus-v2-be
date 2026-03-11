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
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        
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
            # Use sync call for now if async is tricky with the new client in this context, 
            # but google-genai supports both.
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

gemini_service = GeminiService()
