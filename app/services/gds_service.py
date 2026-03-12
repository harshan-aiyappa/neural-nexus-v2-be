from app.services.neo4j_service import neo4j_service

class GDSService:
    def get_similarity(self):
        """
        Baseline Similarity using Jaccard on Shared Neighbors.
        In production, this would use GDS Node Similarity.
        """
        query = """
        MATCH (a)-[:CONTAINS|TREATS|ASSOCIATED_WITH]-(shared)-(b)
        WHERE id(a) < id(b)
        WITH a, b, count(shared) as common
        RETURN a.id as node1, b.id as node2, common as similarity_score
        ORDER BY similarity_score DESC
        LIMIT 20
        """
        return neo4j_service.run_query(query)

    def get_communities(self):
        """
        Baseline Community Detection using simple relationship clustering.
        In production, this would use Louvain or Label Propagation.
        """
        query = """
        MATCH (n)
        WITH n, labels(n)[0] as community
        RETURN community, collect(n.id) as nodes, count(n) as size
        ORDER BY size DESC
        """
        return neo4j_service.run_query(query)

    def get_pagerank(self):
        """
        Baseline Centrality using degree centrality.
        In production, this would use PageRank.
        """
        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        RETURN n.id as id, labels(n)[0] as type, count(r) as score
        ORDER BY score DESC
        LIMIT 20
        """
        return neo4j_service.run_query(query)

gds_service = GDSService()
