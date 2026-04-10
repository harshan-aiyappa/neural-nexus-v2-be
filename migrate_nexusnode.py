import asyncio
import os
from neo4j import AsyncGraphDatabase

async def migrate_labels():
    uri = os.getenv("NEO4J_URI", "bolt://10.10.20.144:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")
    
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async with driver.session() as session:
        print("Checking for NexusNode counts...")
        res = await session.run("MATCH (n:NexusNode) RETURN count(n) as count")
        record = await res.single()
        count = record["count"] if record else 0
        print(f"Found {count} nodes with label 'NexusNode'")
        
        if count > 0:
            print("Renaming NexusNode to TherapeuticUse...")
            # CALL apoc.periodic.iterate is better for massive DBs, but 25 nodes is tiny.
            # Using simple MATCH and SET
            await session.run("MATCH (n:NexusNode) SET n:TherapeuticUse REMOVE n:NexusNode")
            print("Label migration complete.")
            
            print("Updating constraints...")
            await session.run("DROP CONSTRAINT nexus_node_id IF EXISTS")
            await session.run("CREATE CONSTRAINT therapeutic_use_id IF NOT EXISTS FOR (n:TherapeuticUse) REQUIRE n.id IS UNIQUE")
            
            print("Updating indices...")
            await session.run("DROP INDEX node_name_idx IF EXISTS")
            await session.run("CREATE INDEX therapeutic_use_name_idx IF NOT EXISTS FOR (n:TherapeuticUse) ON (n.name)")
            print("Schema update complete.")
        else:
            print("No migration needed.")
            
    await driver.close()

if __name__ == "__main__":
    if not os.getenv("NEO4J_PASSWORD"):
        print("Error: NEO4J_PASSWORD environment variable not set.")
    else:
        asyncio.run(migrate_labels())
