import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/app")

from app.services.neo4j_service import neo4j_service
from app.db.mongo_utils import mongo_service
import asyncio

async def wipe_databases():
    print("Wiping Neo4j Database...")
    try:
        neo4j_service.run_query("MATCH (n) DETACH DELETE n")
        print("Neo4j Database wiped successfully.")
    except Exception as e:
        print(f"Failed to wipe Neo4j: {e}")

    print("Wiping MongoDB Collections...")
    try:
        if mongo_service.db is not None:
            # Wipe folders and users or any other collections
            names = await mongo_service.db.list_collection_names()
            for collection_name in names:
                await mongo_service.db[collection_name].delete_many({})
            print("MongoDB wiped successfully.")
        else:
            print("MongoDB not initialized.")
    except Exception as e:
        print(f"Failed to wipe MongoDB: {e}")

if __name__ == "__main__":
    asyncio.run(wipe_databases())
