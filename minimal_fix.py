import os
from neo4j import GraphDatabase
from pymongo import MongoClient
from bson import ObjectId

# Hardcoded for speed and safety
NEO4J_URI = "bolt://10.10.20.122:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "harsh221996"
MONGO_URI = "mongodb://10.10.20.122:27017"

VERIFICATION_FOLDER_ID = "69b14d419ffff51bab9e15e8"

def migrate():
    print("Connecting to databases...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.neural_nexus_v2
    
    with driver.session() as session:
        print("Running Neo4j label migration...")
        query = (
            "MATCH (n:Folder_VERIFICATION_FOLDER) "
            "SET n:`Folder_69b14d419ffff51bab9e15e8` "
            "REMOVE n:Folder_VERIFICATION_FOLDER "
            "RETURN count(n) as count"
        )
        result = session.run(query)
        count = result.single()["count"]
        print(f"Migrated {count} nodes in Neo4j.")
        
        print(f"Updating MongoDB node_count for {VERIFICATION_FOLDER_ID}...")
        db.folders.update_one(
            {"_id": ObjectId(VERIFICATION_FOLDER_ID)},
            {"$set": {"node_count": count}}
        )
        print("MongoDB updated.")
    
    driver.close()
    mongo_client.close()

if __name__ == "__main__":
    migrate()
