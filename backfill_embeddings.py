import asyncio
import os
import sys

# Add the project root to sys.path to allow imports from app
sys.path.append(os.getcwd())

from app.services.neo4j_service import neo4j_service
from app.services.gemini_service import gemini_service
from app.logging_utils import logger

async def run_backfill():
    print("--- Starting Global Embedding Backfill ---")
    print("Connecting to Neo4j...")
    try:
        await neo4j_service.verify_connectivity()
        print("Connected. High-fidelity semantic indexing in progress...")
        
        # We'll use the existing method which batch processes everything missing an embedding
        await neo4j_service.process_embeddings_batch()
        
        print("--- Backfill Completed Successfully ---")
        print("All existing nodes now have Gemini embeddings for Advanced RAG.")
    except Exception as e:
        print(f"Backfill failed: {e}")
    finally:
        await neo4j_service.close()

if __name__ == "__main__":
    asyncio.run(run_backfill())
