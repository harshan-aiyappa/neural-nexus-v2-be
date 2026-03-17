import logging
import io
import pandas as pd
from typing import List, Dict, Any, Optional
from pypdf import PdfReader
from app.services.neo4j_service import neo4j_service
from app.db.neo4j_utils import symmetry_guardian
from app.services.gemini_service import gemini_service
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

class IngestionService:
    """
    Consolidated Ingestion Service that uses Symmetry Guardian 
    to maintain data integrity and dynamic knowledge extraction.
    """
    
    async def ingest_nodes_rels(self, nodes: List[Dict], rtype_rels: List[Dict], folder_id: str, user_email: str = "System"):
        """Standard ingestion flow with Guardian protection and Audit Logging."""
        logger.info(f"Ingesting {len(nodes)} nodes into {folder_id} for {user_email}...")
        
        try:
            # 1. Ingest into Neo4j
            await neo4j_service.merge_entities_with_guardian(nodes, rtype_rels, folder_id)
            
            # 2. Trigger Symmetry Sync
            await symmetry_guardian.sync_folder_stats(folder_id)
            
            # 3. Invalidate Analytics Cache
            # 4. Log Audit Event
            await audit_service.log_event(
                user_email=user_email,
                action="INGEST",
                resource_type="FOLDER",
                resource_id=folder_id,
                details={"node_count": len(nodes), "rel_count": len(rtype_rels)}
            )
            
            return {"status": "success", "nodes": len(nodes), "rels": len(rtype_rels)}
        except Exception as e:
            logger.error(f"IngestService failure: {e}")
            return {"status": "error", "message": str(e)}

    async def ingest_from_any_source(self, file_content: bytes, filename: str, folder_id: str, user_email: str = "System", use_ai: bool = True):
        """
        Universal Pipeline:
        1. Extract Text (PDF/Excel/CSV/TXT)
        2. Gemini Reasoning (Entity/Relationship extraction)
        3. Scoped Ingestion
        """
        text_content = ""
        nodes = []
        relationships = []

        try:
            # Step 1: Extraction
            if filename.endswith(".pdf"):
                reader = PdfReader(io.BytesIO(file_content))
                text_content = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            elif filename.endswith((".xlsx", ".csv")):
                df = pd.read_excel(io.BytesIO(file_content)) if filename.endswith(".xlsx") else pd.read_csv(io.BytesIO(file_content))
                text_content = df.to_csv(index=False) # Simplest way to pass structured data to LLM
            else:
                text_content = file_content.decode("utf-8")

            if not text_content.strip():
                return {"status": "error", "message": "No text content extracted"}

            # Step 2: Gemini Extraction (AI-Driven)
            if use_ai:
                logger.info(f"Triggering Gemini extraction for {filename}...")
                data = await gemini_service.extract_scientific_entities(text_content)
                nodes = data.get("nodes", [])
                relationships = data.get("relationships", [])
            
            if not nodes:
                return {"status": "warning", "message": "Extraction yielded no entities. Ensure text is relevant."}

            # Step 3: Ingest
            res = await self.ingest_nodes_rels(nodes, relationships, folder_id, user_email=user_email)
            
            # Step 4: Background Embeddings (Implicitly handled by neo4j_service in next sync or task)
            return {
                "status": "success", 
                "filename": filename, 
                "entities_found": len(nodes), 
                "relationships_found": len(relationships)
            }

        except Exception as e:
            logger.error(f"Universal Ingestion failed: {e}")
            return {"status": "error", "message": str(e)}

    async def ingest_cypher_bulk(self, cypher: str, folder_id: str, user_email: str = "System"):
        """Bulk cypher ingestion with scoping and audit logging."""
        try:
            await neo4j_service.execute_cypher_scoped(cypher, folder_id)
            await symmetry_guardian.sync_folder_stats(folder_id)
            symmetry_guardian.clear_analytics_cache(folder_id)
            await audit_service.log_event(
                user_email=user_email,
                action="BULK_CYPHER",
                resource_type="FOLDER",
                resource_id=folder_id
            )
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
        
    @celery_app.task(name="tasks.universal_ingest")
    def universal_ingest_task(file_content: bytes, filename: str, folder_id: str, use_ai: bool, user_email: str = "System"):
        """Celery task for universal ingestion flow."""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(ingest_service.ingest_from_any_source(file_content, filename, folder_id, user_email, use_ai))
except (ImportError, Exception):
    bulk_cypher_ingest_task = None
    universal_ingest_task = None

ingest_service = IngestionService()
