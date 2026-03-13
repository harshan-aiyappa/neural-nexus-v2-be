from app.services.neo4j_service import neo4j_service
from typing import Optional

class GDSService:
    async def get_similarity(self, folder_id: Optional[str] = None):
        """
        Phytochemical Similarity: Finds Herbs that share the same Chemical constituents.
        This is a multi-modal analysis (Herb -> Chemical <- Herb).
        """
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (h1:Herb{label_filter})-[:CONTAINS]->(c:Chemical{label_filter})<-[:CONTAINS]-(h2:Herb{label_filter})
        WHERE elementId(h1) < elementId(h2)
        WITH h1, h2, count(c) as shared_chemicals
        RETURN coalesce(h1.name, h1.id) as herb1, coalesce(h2.name, h2.id) as herb2, shared_chemicals as score
        ORDER BY score DESC
        LIMIT 50
        """
        return await neo4j_service.run_query(query)

    async def get_communities(self, folder_id: Optional[str] = None):
        """
        Cross-Domain Community Detection: Groups entities by their shared therapeutic effects.
        (Herb -> Effect <- Illness).
        """
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (n{label_filter})
        OPTIONAL MATCH (n)-[:TREATS|CAUSES|ASSOCIATED_WITH]-(m{label_filter})
        WITH n, labels(n)[0] as type, count(m) as connectivity
        RETURN type as community, collect(coalesce(n.name, n.id)) as nodes, sum(connectivity) as weight
        ORDER BY weight DESC
        """
        return await neo4j_service.run_query(query)

    async def get_pagerank(self, folder_id: Optional[str] = None):
        """
        Multi-hop Influence Scoring: Identifies critical hub entities (e.g., core chemicals or universal remedies).
        Calculates influence based on incoming treatment and extraction paths.
        """
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        query = f"""
        MATCH (n{label_filter})
        OPTIONAL MATCH (m{label_filter})-[r:CONTAINS|TREATS|EXTRACTED_FROM]->(n)
        WITH n, count(r) as incoming_flow
        RETURN coalesce(n.name, n.id) as name, labels(n)[0] as type, incoming_flow as score
        ORDER BY score DESC
        LIMIT 50
        """
        return await neo4j_service.run_query(query)

gds_service = GDSService()
