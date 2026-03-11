from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

client = genai.Client(api_key=api_key)

print(f"Testing basic generation with {model_name}...")
try:
    response = client.models.generate_content(
        model=model_name,
        contents="Say 'API connection successful' if you see this."
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
