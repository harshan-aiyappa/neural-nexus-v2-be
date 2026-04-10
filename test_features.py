import asyncio
import httpx

async def test_features():
    print("--- Verifying Backend Features ---")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Test /folders (GET)
            folders_resp = await client.get("http://10.10.20.144:8000/folders")
            print(f"GET /folders: {folders_resp.status_code} - {folders_resp.json()}")

            # 2. Test /folders (POST) - Create a Test Folder
            new_folder = {"name": "Test Science", "description": "Verification Folder"}
            create_resp = await client.post("http://10.10.20.144:8000/folders", json=new_folder)
            print(f"POST /folders: {create_resp.status_code} - {create_resp.json()}")
            
            created_folder_id = create_resp.json().get("id")

            # 3. Test /extract (POST)
            extract_req = {"text": "Aspirin is a salicylate drug, often used as an analgesic to relieve minor aches and pains."}
            extract_resp = await client.post("http://10.10.20.144:8000/extract", json=extract_req)
            print(f"POST /extract (Gemini): {extract_resp.status_code}")
            if extract_resp.status_code == 200:
                print("Extraction successful.")
            
            # 4. Clean up Test Folder
            if created_folder_id:
                delete_resp = await client.delete(f"http://10.10.20.144:8000/folders/{created_folder_id}")
                print(f"DELETE /folders: {delete_resp.status_code} - {delete_resp.json()}")

        except Exception as e:
            print(f"Feature verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_features())
