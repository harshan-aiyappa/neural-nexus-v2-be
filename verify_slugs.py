import asyncio
import httpx

async def verify_slugs():
    print("--- Verifying Folder Slugs ---")
    
    # Generate a temporary test token
    from jose import jwt
    from datetime import datetime, timedelta
    SECRET_KEY = "neural-nexus-v2-master-secret-0912384756"
    ALGORITHM = "HS256"
    token_data = {"sub": "test@example.com", "role": "ADMIN", "exp": datetime.utcnow() + timedelta(minutes=10)}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Test /folders (GET)
            folders_resp = await client.get("http://10.10.20.144:8000/api/folders/", headers=headers)
            print(f"GET /api/folders/: {folders_resp.status_code}")
            folders = folders_resp.json()
            
            if folders_resp.status_code != 200:
                print(f"GET failed: {folders_resp.text}")
                return

            folders = folders_resp.json()
            if isinstance(folders, list) and folders:
                for f in folders:
                    print(f"Folder: {f['name']}, Slug: {f.get('slug')}")
                    if not f.get('slug'):
                        print("FAILED: Slug missing!")
                    else:
                        print("SUCCESS: Slug found.")
            else:
                print("No folders found or invalid format. Creating one...")
                new_folder = {"name": "Verification Folder", "description": "Verification"}
                create_resp = await client.post("http://10.10.20.144:8000/api/folders/", json=new_folder, headers=headers)
                print(f"POST /api/folders/: {create_resp.status_code}")
                if create_resp.status_code != 200:
                    print(f"POST failed: {create_resp.text}")
                
                # Re-fetch
                folders_resp = await client.get("http://10.10.20.144:8000/api/folders/", headers=headers)
                folders = folders_resp.json()
                if isinstance(folders, list):
                    for f in folders:
                        print(f"Folder: {f['name']}, Slug: {f.get('slug')}")
                else:
                    print(f"Final fetch failed: {folders}")

        except Exception as e:
            print(f"Verification failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_slugs())
