from pymongo import MongoClient
import os

def fix_slugs():
    mc = MongoClient('mongodb://10.10.20.144:27017')
    db = mc.neural_nexus_v2
    collection = db.get_collection("folders")
    
    # Update Verification Folder
    collection.update_one(
        {"name": "Verification Folder"},
        {"$set": {"slug": "verification-folder"}}
    )
    
    # Update Phytochemical KG
    collection.update_one(
        {"name": "Phytochemical KG"},
        {"$set": {"slug": "phytochemical-kg"}}
    )
    
    # Verify
    for f in collection.find({}):
        print(f"Name: {f.get('name')} | Slug: {f.get('slug')} | ID: {str(f['_id'])}")
    
    mc.close()

if __name__ == "__main__":
    fix_slugs()
