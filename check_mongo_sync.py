import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def check_mongo():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client.get_database("neural_nexus_v2")
        print("--- MongoDB Status ---")
        collections = db.list_collection_names()
        print(f"Collections: {collections}")
        for coll_name in collections:
            count = db.get_collection(coll_name).count_documents({})
            print(f"Collection '{coll_name}': {count} documents")
            if count > 0:
                sample = db.get_collection(coll_name).find_one()
                print(f"Sample from {coll_name}: {sample}")
    except Exception as e:
        print(f"MongoDB Error: {e}")

if __name__ == "__main__":
    check_mongo()
