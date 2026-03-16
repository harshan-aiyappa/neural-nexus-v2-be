from datetime import datetime
from app.logging_utils import db_logger
from app.services.neo4j_service import neo4j_service
from app.db.mongo_utils import mongo_service
from app.services.cache_service import cache_service
from bson import ObjectId

class SymmetryGuardian:
    """
    The Symmetry Guardian ensures data integrity and consistency between 
    Neo4j (Knowledge Graph) and MongoDB (Metadata/Activity).
    """

    @staticmethod
    def clear_analytics_cache(folder_id: str):
        """Invalidates all cached GDS results for a specific folder."""
        try:
            keys = [
                f"gds:similarity:{folder_id}",
                f"gds:communities:{folder_id}",
                f"gds:pagerank:{folder_id}"
            ]
            for key in keys:
                cache_service.delete(key)
            db_logger.info(f"SymmetryGuardian: Invalidated GDS cache for folder {folder_id}")
        except Exception as e:
            db_logger.error(f"SymmetryGuardian Cache Clear Failed: {e}")
    
    @staticmethod
    async def sync_folder_stats(folder_id: str):
        """
        Synchronizes MongoDB folder metadata with the actual Neo4j graph state.
        This ensures 'node_count' and 'updated_at' are accurate.
        """
        try:
            # 1. Get real count from Neo4j
            counts = await neo4j_service.get_folder_node_counts()
            real_count = counts.get(folder_id, 0)
            
            # 2. Update MongoDB
            collection = mongo_service.db.get_collection("folders")
            await collection.update_one(
                {"_id": ObjectId(folder_id)},
                {
                    "$set": {
                        "node_count": real_count,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            )
            db_logger.info(f"SymmetryGuardian: Synced folder {folder_id} Stats -> {real_count} nodes")
            return real_count
        except Exception as e:
            db_logger.error(f"SymmetryGuardian Sync Failed: {e}")
            return None

    @staticmethod
    async def atomic_delete_folder(folder_id: str):
        """
        Performs a cross-database deletion to ensure no orphaned data remains.
        Wipes graph nodes (Neo4j) and metadata (MongoDB).
        """
        db_logger.info(f"SymmetryGuardian: Executing atomic delete for folder {folder_id}")
        
        try:
            # 1. Delete from Neo4j (Scoped delete)
            # Efficiently delete all nodes with the folder label
            folder_label = f"Folder_{folder_id}"
            cypher = f"MATCH (n:`{folder_label}`) DETACH DELETE n"
            await neo4j_service.execute_cypher(cypher)
            
            # 2. Delete from MongoDB
            await mongo_service.delete_folder(folder_id)
            
            # 3. Invalidate Analytics Cache
            SymmetryGuardian.clear_analytics_cache(folder_id)
            
            db_logger.info(f"SymmetryGuardian: Atomic delete successful for {folder_id}")
            return True
        except Exception as e:
            db_logger.error(f"SymmetryGuardian Atomic Delete Failed: {e}")
            return False

# Export instance for easy use
symmetry_guardian = SymmetryGuardian()
