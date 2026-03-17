from typing import Any, Dict, Optional
from datetime import datetime
from app.db.mongo_utils import mongo_service
from app.logging_utils import logger

class AuditService:
    """
    Enterprise Governance Service:
    Tracks all ingestion, deletion, and modification events for auditability.
    """
    
    async def log_event(
        self, 
        user_email: str, 
        action: str, 
        resource_type: str, 
        resource_id: str, 
        details: Optional[Dict[str, Any]] = None
    ):
        try:
            collection = mongo_service.db.get_collection("audit_logs")
            log_entry = {
                "user": user_email,
                "action": action, # 'INGEST', 'UPDATE', 'DELETE', 'CREATE'
                "resource_type": resource_type, # 'NODE', 'RELATIONSHIP', 'FOLDER', 'FILE'
                "resource_id": resource_id,
                "details": details or {},
                "timestamp": datetime.utcnow()
            }
            await collection.insert_one(log_entry)
            logger.info(f"[AUDIT] {user_email} performed {action} on {resource_type}:{resource_id}")
        except Exception as e:
            logger.error(f"Audit log failure: {e}")

    async def get_activity_stream(self, limit: int = 50):
        """Returns the most recent audit events for the Activity Stream UI."""
        try:
            collection = mongo_service.db.get_collection("audit_logs")
            cursor = collection.find().sort("timestamp", -1).limit(limit)
            logs = await cursor.to_list(length=limit)
            for log in logs:
                log["id"] = str(log.pop("_id"))
            return logs
        except Exception as e:
            logger.error(f"Activity stream fetch failure: {e}")
            return []

audit_service = AuditService()
