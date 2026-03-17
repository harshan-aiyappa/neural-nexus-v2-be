import asyncio
from app.core.celery_app import celery_app
from app.services.neo4j_service import neo4j_service
from app.logging_utils import db_logger

@celery_app.task(name="tasks.process_embeddings_backfill")
def process_embeddings_task(folder_id: str = None):
    """
    Celery task to run the embedding backfill process.
    Wraps the async method in a sync Celery worker context.
    """
    db_logger.info(f"CELERY: Starting embedding backfill for folder: {folder_id or 'all'}")
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(neo4j_service.process_embeddings_batch(folder_id))

@celery_app.task(name="tasks.bulk_node_update")
def bulk_node_update_task(node_ids: list, properties: dict):
    """
    Celery task for bulk property updates.
    """
    async def _update_all():
        for nid in node_ids:
            await neo4j_service.update_node(nid, properties)
    
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_update_all())
