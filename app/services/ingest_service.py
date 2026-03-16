import logging
from typing import List, Dict, Any
from app.services.neo4j_service import neo4j_service
from app.db.neo4j_utils import symmetry_guardian

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Consolidated Ingestion Service that uses Symmetry Guardian 
    to maintain data integrity.
    """
    
    async def ingest_nodes_rels(self, nodes: List[Dict], rtype_rels: List[Dict], folder_id: str):
        """Standard ingestion flow with Guardian protection."""
        logger.info(f"Ingesting {len(nodes)} nodes into {folder_id}...")
        
        try:
            # 1. Ingest into Neo4j
            await neo4j_service.merge_entities_with_guardian(nodes, rtype_rels, folder_id)
            
            # 2. Trigger Symmetry Sync (The Guardian's main job)
            await symmetry_guardian.sync_folder_stats(folder_id)
            
            # 3. Invalidate Analytics Cache (New Phase 19)
            symmetry_guardian.clear_analytics_cache(folder_id)
            
            return {"status": "success", "nodes": len(nodes), "rels": len(rtype_rels)}
        except Exception as e:
            logger.error(f"IngestService failure: {e}")
            return {"status": "error", "message": str(e)}

    async def ingest_cypher_bulk(self, cypher: str, folder_id: str):
        """Bulk cypher ingestion with scoping and stats sync."""
        try:
            await neo4j_service.execute_cypher_scoped(cypher, folder_id)
            await symmetry_guardian.sync_folder_stats(folder_id)
            # Invalidate Analytics Cache
            symmetry_guardian.clear_analytics_cache(folder_id)
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Cypher ingestion fail: {e}")
            return {"status": "error", "message": str(e)}

# Celery Task Wrapper for Heavy Background Ingestion
try:
    from app.core.celery_app import celery_app
    import asyncio

    @celery_app.task(name="tasks.bulk_cypher_ingest")
    def bulk_cypher_ingest_task(cypher: str, folder_id: str):
        """Celery task to run bulk cypher ingestion in background."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(ingest_service.ingest_cypher_bulk(cypher, folder_id))
except (ImportError, Exception):
    bulk_cypher_ingest_task = None

ingest_service = IngestionService()
