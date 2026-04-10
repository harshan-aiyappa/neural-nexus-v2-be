import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to allow importing app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.neo4j_service import neo4j_service
from app.db.mongo_utils import mongo_service
import re

def slugify(text):
    return re.sub(r'[\W_]+', '_', text).upper()

from typing import List, Dict, Optional
import asyncio

async def clear_and_sync_semantic():
    print("Cleaning Mongo data...")
    await mongo_service.db.get_collection("folders").delete_many({})
    await mongo_service.db.get_collection("documents").delete_many({})
    
    # Create Semantic Folders
    folder_a_name = "Herb Research"
    folder_b_name = "Academic Archive"
    
    folder_a_id = await mongo_service.create_folder(folder_a_name, "Primary repository for seeded Herb entities")
    folder_b_id = await mongo_service.create_folder(folder_b_name, "Historical academic datasets")
    
    return [
        {"id": folder_a_id, "name": folder_a_name, "slug": slugify(folder_a_name)},
        {"id": folder_b_id, "name": folder_b_name, "slug": slugify(folder_b_name)}
    ]

def transform_cypher(cypher, slug):
    """Transform Cypher to use semantic labels without altering IDs."""
    
    # Add folder label to CREATE statements
    # Match CREATE (n:Label {...)
    # We want (n:Label:Folder_SLUG {...)
    cypher = re.sub(r"CREATE\s+\(([a-z0-9]+):([A-Za-z]+)", f"CREATE (\\1:\\2:Folder_{slug}", cypher)
    
    return cypher

async def seed():
    print("--- Starting Semantic Database Seeding ---")
    cypher_path = os.path.join(os.path.dirname(__file__), "seed_data.cypher")
    
    if not os.path.exists(cypher_path):
        print(f"Error: {cypher_path} not found.")
        return

    with open(cypher_path, "r") as f:
        original_cypher = f.read()

    # Clear Neo4j
    print("Cleaning existing graph data...")
    await neo4j_service.run_write_query("MATCH (n) DETACH DELETE n")
    
    # Handle Mongo and get folder info
    folders = await clear_and_sync_semantic()

    # Apply data for each folder with its own namespace
    for folder in folders:
        print(f"Seeding folder: {folder['name']} (Label: Folder_{folder['slug']})")
        semantic_cypher = transform_cypher(original_cypher, folder['slug'])
        await neo4j_service.execute_cypher(semantic_cypher)
        
    print("Seed process complete. Data is now semantically isolated.")

if __name__ == "__main__":
    asyncio.run(seed())
