import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

async def check_databases():
    # Check MongoDB
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://10.10.20.144:27017")
    client = AsyncIOMotorClient(mongo_uri)
    db = client.get_database("neural_nexus_v2")
    
    print("--- MongoDB Status ---")
    collections = await db.list_collection_names()
    print(f"Collections: {collections}")
    
    for coll_name in collections:
        count = await db.get_collection(coll_name).count_documents({})
        print(f"Collection '{coll_name}': {count} documents")
        if count > 0:
            sample = await db.get_collection(coll_name).find_one()
            # Convert ObjectId to string for printing
            if sample and '_id' in sample:
                sample['_id'] = str(sample['_id'])
            print(f"Sample from {coll_name}: {sample}")

    # Check Neo4j
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://10.10.20.144:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    print("\n--- Neo4j Status ---")
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        with driver.session() as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            labels = session.run("CALL db.labels()").value()
            
            print(f"Node Count: {node_count}")
            print(f"Relationship Count: {rel_count}")
            print(f"Labels: {labels}")
            
            if node_count > 0:
                sample_node = session.run("MATCH (n) RETURN n LIMIT 1").single()["n"]
                print(f"Sample Node: {sample_node}")
        driver.close()
    except Exception as e:
        print(f"Neo4j Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_databases())
