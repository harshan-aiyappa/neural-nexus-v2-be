import asyncio
import httpx
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

async def check_backend():
    print("Checking Backend health...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://localhost:8000/health")
            print(f"Backend Health: {resp.status_code} - {resp.json()}")
            
            resp_mongo = await client.get("http://localhost:8000/health/mongo")
            print(f"MongoDB Health: {resp_mongo.status_code} - {resp_mongo.json()}")
        except Exception as e:
            print(f"Backend/Mongo check failed: {e}")

def check_neo4j():
    print("Checking Neo4j health...")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as n")
            record = result.single()
            print(f"Neo4j Connection: OK (Result: {record['n']})")
        driver.close()
    except Exception as e:
        print(f"Neo4j connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_backend())
    check_neo4j()
