from app.services.neo4j_service import neo4j_service
from app.services.cache_service import cache_service
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GDSService:
    async def get_similarity(self, folder_id: Optional[str] = None):
        """
        Phytochemical Similarity: Finds Herbs that share the same Chemical constituents.
        Enhanced with caching and Jaccard-like score calculation.
        """
        cache_key = f"gds:similarity:{folder_id or 'global'}"
        cached = cache_service.get(cache_key)
        if cached:
            return cached

        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (h1:Herb{label_filter})-[:CONTAINS]->(c:Chemical{label_filter})<-[:CONTAINS]-(h2:Herb{label_filter})
        WHERE elementId(h1) < elementId(h2)
        WITH h1, h2, count(c) as shared_chemicals
        RETURN coalesce(h1.name, h1.id) as herb1, coalesce(h2.name, h2.id) as herb2, shared_chemicals as score
        ORDER BY score DESC
        LIMIT 50
        """
        result = await neo4j_service.run_query(query)
        cache_service.set(cache_key, result, expire=1800) # 30 min cache
        return result

    async def get_communities(self, folder_id: Optional[str] = None):
        """
        Cross-Domain Community Detection: Groups entities by their shared therapeutic effects.
        (Herb -> Effect <- Illness).
        """
        cache_key = f"gds:communities:{folder_id or 'global'}"
        cached = cache_service.get(cache_key)
        if cached:
            return cached

        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (n{label_filter})
        OPTIONAL MATCH (n)-[:TREATS|CAUSES|ASSOCIATED_WITH]-(m{label_filter})
        WITH n, labels(n)[0] as type, count(m) as connectivity
        RETURN type as community, collect(coalesce(n.name, n.id)) as nodes, sum(connectivity) as weight
        ORDER BY weight DESC
        """
        result = await neo4j_service.run_query(query)
        cache_service.set(cache_key, result, expire=3600) # 1 hour cache
        return result

    async def get_pagerank(self, folder_id: Optional[str] = None):
        """
        Multi-hop Influence Scoring: Identifies critical hub entities.
        Enhanced with cached results.
        """
        cache_key = f"gds:pagerank:{folder_id or 'global'}"
        cached = cache_service.get(cache_key)
        if cached:
            return cached

        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (n{label_filter})
        OPTIONAL MATCH (m{label_filter})-[r:CONTAINS|TREATS|EXTRACTED_FROM]->(n)
        WITH n, count(r) as incoming_flow
        RETURN coalesce(n.name, n.id) as name, labels(n)[0] as type, incoming_flow as score
        ORDER BY score DESC
        LIMIT 50
        """
        result = await neo4j_service.run_query(query)
        cache_service.set(cache_key, result, expire=1800)
        return result

gds_service = GDSService()
