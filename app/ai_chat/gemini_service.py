import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class ChatGeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def generate(self, prompt: str) -> str:
        try:
            # We use the sync client here in a standard way, but we can wrap it if needed.
            # Using basic generation since GenAI doesn't have an async `generate_content` readily exposed in basic usage, 
            # though it supports standard blocking calls.
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            from app.logging_utils import ai_logger
            ai_logger.error(f"Chat Gemini generation error: {str(e)}")
            return f"Gemini generation error: {str(e)}"

    async def generate_with_config(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            return response.text
        except Exception as e:
            from app.logging_utils import ai_logger
            ai_logger.error(f"Chat Gemini generation config error: {str(e)}")
            return f"Gemini generation error: {str(e)}"

chat_gemini_service = ChatGeminiService()
