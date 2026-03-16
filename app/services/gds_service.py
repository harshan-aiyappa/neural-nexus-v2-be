from app.services.neo4j_service import neo4j_service
from app.services.cache_service import cache_service
from typing import Optional
from app.logging_utils import db_logger

class GDSService:
    async def get_similarity(self, folder_id: Optional[str] = None):
        """
        Phytochemical Similarity: Finds Herbs that share the same Chemical constituents.
        Enhanced with Jaccard-like logic for multi-way overlap.
        """
        fid = folder_id or "global"
        cache_key = f"gds:similarity:{fid}"
        cached = cache_service.get(cache_key)
        if cached:
            db_logger.info(f"GDS Similarity: Cache hit for {fid}")
            return cached
        
        db_logger.info(f"GDS Similarity: Cache miss for {fid}. Computing...")

        label_filter = f":Folder_{folder_id}" if folder_id else ""
        # Multi-way overlap: Herb -> Compound -> (Same) Compound -> Herb
        query = f"""
        MATCH (h1:Herb{label_filter})-[:CONTAINS]->(c:Chemical{label_filter})<-[:CONTAINS]-(h2:Herb{label_filter})
        WHERE elementId(h1) < elementId(h2)
        WITH h1, h2, count(DISTINCT c) as shared_chemicals
        MATCH (h1)-[:CONTAINS]->(all_c1)
        MATCH (h2)-[:CONTAINS]->(all_c2)
        WITH h1, h2, shared_chemicals, count(DISTINCT all_c1) + count(DISTINCT all_c2) - shared_chemicals as union_size
        RETURN coalesce(h1.name, h1.id) as herb1, coalesce(h2.name, h2.id) as herb2, 
               round(toFloat(shared_chemicals)/union_size * 100, 2) as score
        ORDER BY score DESC
        LIMIT 50
        """
        result = await neo4j_service.run_query(query)
        cache_service.set(cache_key, result, expire=1800)
        return result

    async def get_communities(self, folder_id: Optional[str] = None):
        """
        Cross-Domain Community Detection: Groups entities by shared therapeutic target paths.
        Heterogeneous Path: (Herb -> Chemical -> Biomarker <- Disease).
        """
        fid = folder_id or "global"
        cache_key = f"gds:communities:{fid}"
        cached = cache_service.get(cache_key)
        if cached:
            db_logger.info(f"GDS Communities: Cache hit for {fid}")
            return cached
        
        db_logger.info(f"GDS Communities: Cache miss for {fid}. Computing...")

        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (n{label_filter})-[*1..2]-(m{label_filter})
        WITH n, labels(n)[0] as type, count(DISTINCT labels(m)[0]) as diversity
        RETURN type as community, collect(DISTINCT coalesce(n.name, n.id)) as nodes, sum(diversity) as weight
        ORDER BY weight DESC
        """
        result = await neo4j_service.run_query(query)
        cache_service.set(cache_key, result, expire=3600)
        return result

    async def get_pagerank(self, folder_id: Optional[str] = None):
        """
        Indirected Influence Scoring: Identifies critical hub entities via heterogeneous links.
        """
        fid = folder_id or "global"
        cache_key = f"gds:pagerank:{fid}"
        cached = cache_service.get(cache_key)
        if cached:
            db_logger.info(f"GDS PageRank: Cache hit for {fid}")
            return cached
        
        db_logger.info(f"GDS PageRank: Cache miss for {fid}. Computing...")

        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (n{label_filter})
        OPTIONAL MATCH (n)-[r]-(m{label_filter})
        WITH n, count(DISTINCT r) as hub_score
        RETURN coalesce(n.name, n.id) as name, labels(n)[0] as type, hub_score as score
        ORDER BY score DESC
        LIMIT 50
        """
        result = await neo4j_service.run_query(query)
        cache_service.set(cache_key, result, expire=1800)
        return result

gds_service = GDSService()
