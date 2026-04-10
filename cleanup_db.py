from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def cleanup_duplicates():
    uri = os.getenv("MONGODB_URI", "mongodb://10.10.20.144:27017")
    client = AsyncIOMotorClient(uri)
    db = client.get_database("neural_nexus_v2")
    collection = db.get_collection("folders")
    
    # Delete all folders named "Herb Knowledge" or "Bioactives Discovery" to start fresh
    result = await collection.delete_many({"name": {"$in": ["Herb Knowledge", "Bioactives Discovery"]}})
    print(f"Deleted {result.deleted_count} duplicate folders.")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
