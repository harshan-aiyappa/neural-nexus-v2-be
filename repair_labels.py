import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.db.mongo_utils import mongo_service
from app.services.neo4j_service import neo4j_service

async def repair_labels():
    print("Fetching folders from MongoDB...")
    folders = await mongo_service.get_all_folders()
    
    # Map name -> id
    name_to_id = {f['name']: f['id'] for f in folders}
    print(f"Found folders in MongoDB: {name_to_id}")
    
    # Check for legacy labels in Neo4j
    counts = await neo4j_service.get_folder_node_counts()
    print(f"Current labels in Neo4j: {counts}")
    
    for name, folder_id in name_to_id.items():
        # Possible legacy labels
        legacy_slug = neo4j_service.slugify_folder(name)
        legacy_label_slug = f"Folder_{legacy_slug}"
        legacy_label_caps = f"Folder_{name.upper().replace(' ', '_')}"
        
        # Check if either exists but the real ID label doesn't have the full count
        # (This is a simplified check, we'll just migrate whatever we find)
        
        for legacy in [legacy_label_slug, legacy_label_caps]:
            # Use raw query to rename labels
            # In Neo4j, you can't easily rename a label for all nodes without iterate,
            # but for 20 nodes, a simple MATCH/SET is fine.
            query = f"MATCH (n:`{legacy}`) SET n:`Folder_{folder_id}` REMOVE n:`{legacy}`"
            res = await neo4j_service.execute_cypher(query)
            if res.get('results') and res['results'][0].get('_labels_added', 0) > 0:
                print(f"Migrated nodes from {legacy} to Folder_{folder_id}")

if __name__ == "__main__":
    asyncio.run(repair_labels())
