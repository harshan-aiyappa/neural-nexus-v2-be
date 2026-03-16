import asyncio
import os
import sys

sys.path.append(os.getcwd())
from app.services.neo4j_service import neo4j_service

async def verify():
    print("Verifying semantic indexing status...")
    await neo4j_service.verify_connectivity()
    query = "MATCH (n) WHERE n.embedding IS NULL AND n.name IS NOT NULL RETURN count(n) as count"
    res = await neo4j_service.run_query(query)
    count = res[0]['count']
    print(f"Nodes missing embeddings: {count}")
    if count == 0:
        print("SUCCESS: All folders are fully vectorized.")
    else:
        print(f"NOTE: {count} nodes still missing embeddings. Run backfill again.")
    await neo4j_service.close()

if __name__ == "__main__":
    asyncio.run(verify())
