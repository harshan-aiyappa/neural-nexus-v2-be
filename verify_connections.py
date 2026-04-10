import asyncio
import httpx
from neo4j import GraphDatabase
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def check_backend():
    print("\n--- Checking Backend API ---")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://10.10.20.144:8000/")
            print(f"Backend Health (10.10.20.144:8000): {resp.status_code} - OK")
        except Exception as e:
            print(f"Backend check failed: {e}")

async def check_mongodb():
    print("\n--- Checking MongoDB ---")
    uri = os.getenv("MONGODB_URI", "mongodb://10.10.20.144:27017")
    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=2000)
        # Try a ping
        await client.admin.command('ping')
        print(f"MongoDB Connection ({uri}): OK")
        
        # Check database access
        db = client['neural_nexus_v2']
        collections = await db.list_collection_names()
        print(f"MongoDB Collections: {collections}")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")

def check_neo4j():
    print("\n--- Checking Neo4j ---")
    uri = os.getenv("NEO4J_URI", "bolt://10.10.20.144:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as n")
            record = result.single()
            print(f"Neo4j Connection ({uri}): OK")
        driver.close()
    except Exception as e:
        print(f"Neo4j connection failed: {e}")

async def main():
    await check_backend()
    await check_mongodb()
    check_neo4j()
    print("\n--- All checks complete ---")

if __name__ == "__main__":
    asyncio.run(main())
