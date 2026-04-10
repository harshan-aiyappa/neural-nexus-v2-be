from neo4j import GraphDatabase
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

def audit():
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://10.10.20.144:27017")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://10.10.20.144:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    mc = MongoClient(mongo_uri)
    db = mc.neural_nexus_v2
    folders = list(db.folders.find({}))
    
    print("--- MONGODB FOLDERS ---")
    for f in folders:
        print(f"Name: {f['name']}")
        print(f"  ID: {f['_id']}")
        print(f"  Slug: {f.get('slug')}")
        print(f"  Node Count: {f.get('node_count')}")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    with driver.session() as session:
        print("\n--- NEO4J LABELS ---")
        labels = session.run("CALL db.labels() YIELD label WHERE label STARTS WITH 'Folder_' RETURN label").data()
        for l in labels:
            label = l['label']
            count = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count").single()[0]
            print(f"Label: {label} -> Count: {count}")
    
    driver.close()
    mc.close()

if __name__ == '__main__':
    audit()
