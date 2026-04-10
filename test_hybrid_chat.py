import asyncio
import httpx
import json

async def test_hybrid_chat():
    base_url = "http://10.10.20.144:8000/api"
    
    chat_req = {
        "message": "What can you tell me about the plant Tulasi?",
        "context_folder": "plant-science-v2" # Assuming this folder exists or use a real one
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("Sending chat request...")
            # Note: We might need a JWT if the endpoint is protected
            # For testing, we can use a mock token or temporarily disable auth if needed
            # But let's try calling it.
            resp = await client.post(f"{base_url}/chat", json=chat_req, timeout=30.0)
            
            if resp.status_code == 200:
                print("SUCCESS: Chat response received.")
                print(json.dumps(resp.json(), indent=2))
                print("\nVerification: Check Neo4j for :ChatMessage nodes and MongoDB for 'chat_history' records.")
            else:
                print(f"FAILED: Status {resp.status_code}")
                print(resp.text)
                
        except Exception as e:
            print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_chat())
