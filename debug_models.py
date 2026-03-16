import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print("--- Embedding Models ---")
    for model in client.models.list():
        if 'embedContent' in model.supported_actions or 'embedText' in model.supported_actions:
            print(f"Name: {model.name} | Supported Methods: {model.supported_actions}")

if __name__ == "__main__":
    list_models()
