import os
import google.generativeai as genai
from typing import List, Dict, Any
import json
from dotenv import load_dotenv

load_dotenv()

class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    async def extract_scientific_entities(self, text: str) -> Dict[str, Any]:
        """
        Extracts scientific entities and relationships from text using Gemini.
        Strategically designed for cost-efficiency and high precision.
        """
        prompt = f"""
        You are a specialized scientific data extractor for a Knowledge Graph.
        Extract Nodes (Entities) and Relationships (Edges) from the following text.
        
        TEXT:
        \"\"\"{text}\"\"\"
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "nodes": [
                {{ "id": "EntityName", "label": "Label", "properties": {{ "detail": "..." }} }}
            ],
            "relationships": [
                {{ "source": "NodeA", "target": "NodeB", "type": "RELATIONSHIP_TYPE", "properties": {{ "isSymmetric": true/false }} }}
            ]
        }}
        
        RULES:
        1. Labels MUST be highly specific (e.g., Herb, Disease, Chemical, Mechanism).
        2. Relationship types MUST follow the master standard (e.g., TREATS, INHIBITS, ASSOCIATED_WITH).
        3. For undirected associations (e.g., SIMILAR_TO), set isSymmetric: true.
        4. Do not include redundant info.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error during Gemini extraction: {e}")
            return {"nodes": [], "relationships": []}

gemini_service = GeminiService()
