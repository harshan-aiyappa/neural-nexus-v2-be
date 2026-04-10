import asyncio
import httpx
import os

async def trigger_ingestion():
    file_path = r"d:\01_Projects\OpenSource\neural-nexus\Herb modelling example data.xlsx"
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        # 1. Create a folder for the Herb data
        print("Creating 'Herb Knowledge' folder...")
        folder_resp = await client.post("http://10.10.20.144:8000/folders", json={
            "name": "Herb Knowledge",
            "description": "Ingestion from Herb modelling example data.xlsx"
        })
        
        if folder_resp.status_code != 200:
            print("Failed to create folder:", folder_resp.text)
            return
            
        folder_id = folder_resp.json()["id"]
        print(f"Folder created with ID: {folder_id}")
        
        # 2. Trigger Excel Ingestion
        print(f"Triggering ingestion for: {file_path}")
        ingest_resp = await client.post("http://10.10.20.144:8000/ingest/excel", json={
            "file_path": file_path,
            "folder_id": folder_id
        })
        
        print("Ingestion Status:", ingest_resp.status_code)
        print("Result:", ingest_resp.json())

if __name__ == "__main__":
    asyncio.run(trigger_ingestion())
