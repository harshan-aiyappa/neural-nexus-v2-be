import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env from the backend directory
load_dotenv(".env")

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    print(f"--- Testing Gemini API ---")
    print(f"API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")
    print(f"Model: {model_name}")

    if not api_key:
        print("ERROR: No API key found in .env")
        return

    try:
        genai.configure(api_key=api_key)
        
        # 1. Check if we can get the model
        print(f"\nAttempting to get model: models/{model_name}...")
        try:
            model_info = genai.get_model(f"models/{model_name}")
            print(f"✅ Successfully retrieved model info: {model_info.display_name}")
        except Exception as e:
             print(f"❌ Failed to get model '{model_name}': {e}")
             print("Trying fallback to gemini-1.5-flash...")
             model_name = "gemini-1.5-flash"
             model_info = genai.get_model(f"models/{model_name}")
             print(f"✅ Successfully retrieved model info: {model_info.display_name}")

        # 2. Attempt a simple generation
        print("\nAttempting content generation ('Hello world')...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello environment! Are you active?")
        
        print(f"✅ Generation successful!")
        print(f"Response: {response.text.strip()}")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during test: {e}")

if __name__ == "__main__":
    test_gemini()
