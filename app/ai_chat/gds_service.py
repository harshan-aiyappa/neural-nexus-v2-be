from app.services.neo4j_service import neo4j_service

class ChatGDSService:
    # -- Node Similarity --
    async def get_similarity_context(self, limit: int = 10, folder_id: str = "") -> str:
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        try:
            query = f"""
            MATCH (h1:Herb{label_filter})-[:CONTAINS]->(c:Chemical{label_filter})<-[:CONTAINS]-(h2:Herb{label_filter})
            WHERE elementId(h1) < elementId(h2)
            WITH h1, h2, count(DISTINCT c) as shared
            WHERE shared > 0
            WITH h1, h2, shared
            MATCH (h1)-[:CONTAINS]->(all_c1)
            MATCH (h2)-[:CONTAINS]->(all_c2)
            WITH h1, h2, shared, count(DISTINCT all_c1) + count(DISTINCT all_c2) - shared as union_size
            RETURN coalesce(h1.name, coalesce(h1.common_name, h1.id)) as entity1, labels(h1)[0] as type1,
                   coalesce(h2.name, coalesce(h2.common_name, h2.id)) as entity2, labels(h2)[0] as type2,
                   round(toFloat(shared)/union_size * 100) AS similarity_pct
            ORDER BY similarity_pct DESC LIMIT $limit
            """
            similarities = await neo4j_service.run_query(query, {"limit": limit})
            if not similarities:
                return ""
                
            lines = ["Top similar entities in the knowledge graph:"]
            for s in similarities:
                lines.append(f"- {s['entity1']} ({s['type1']}) <-> {s['entity2']} ({s['type2']}): {s['similarity_pct']}% similar")
            return "\n".join(lines)
        except Exception as e:
            return ""

    # -- Community Detection --
    async def get_community_context(self, folder_id: str = "") -> str:
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        try:
            query = f"""
            MATCH (n{label_filter})-[*1..2]-(m{label_filter})
            WITH n, labels(n)[0] as type, count(DISTINCT m) as diversity
            RETURN type as community, collect(DISTINCT coalesce(n.name, n.id)) as members, sum(diversity) as weight
            ORDER BY weight DESC LIMIT 20
            """
            communities = await neo4j_service.run_query(query)
            if not communities:
                return ""

            lines = [f"Community clusters detected ({len(communities)} active clusters):"]
            for i, c in enumerate(communities[:10]):
                members = c["members"]
                names = ", ".join(members[:8])
                extra = f" +{len(members)-8} more" if len(members) > 8 else ""
                lines.append(f"  Cluster {i+1} : {names}{extra}")
            return "\n".join(lines)
        except Exception as e:
            return ""

    # -- Centrality (PageRank-like hub counting) --
    async def get_centrality_context(self, folder_id: str = "", limit: int = 15) -> str:
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        try:
            query = f"""
            MATCH (n{label_filter})-[r]-(m{label_filter})
            WITH n, count(DISTINCT r) as score
            RETURN coalesce(n.name, coalesce(n.common_name, n.id)) as name,
                   labels(n)[0] as type,
                   score
            ORDER BY score DESC LIMIT $limit
            """
            rankings = await neo4j_service.run_query(query, {"limit": limit})
            if not rankings:
                return ""
                
            lines = ["Most important/connected entities:"]
            for r in rankings:
                lines.append(f"  - {r['name']} ({r['type']}): connection score {r['score']}")
            return "\n".join(lines)
        except Exception as e:
            return ""

    # -- Shortest Path --
    async def get_path_context(self, entity1: str, entity2: str, folder_id: str = "") -> str:
        label_filter = f":Folder_{folder_id}" if folder_id else ""
        try:
            query = f"""
            MATCH (a{label_filter}), (b{label_filter})
            WHERE (toLower(coalesce(a.name, a.common_name, a.id, '')) CONTAINS toLower($e1))
              AND (toLower(coalesce(b.name, b.common_name, b.id, '')) CONTAINS toLower($e2))
            WITH a, b LIMIT 1
            MATCH path = shortestPath((a)-[*..10]-(b))
            RETURN [n IN nodes(path) | coalesce(n.name, n.id) + ' (' + labels(n)[0] + ')'] AS path_nodes,
                   [r IN relationships(path) | type(r)] AS path_rels,
                   length(path) AS path_length
            """
            paths = await neo4j_service.run_query(query, {"e1": entity1, "e2": entity2})
            if not paths:
                return f"No path found between '{entity1}' and '{entity2}'."
                
            p = paths[0]
            nodes = p.get("path_nodes", [])
            rels = p.get("path_rels", [])
            chain = []
            for i, node in enumerate(nodes):
                chain.append(node)
                if i < len(rels):
                    chain.append(f"--[{rels[i]}]-->")
            return f"Shortest path ({p['path_length']} hops): {' '.join(chain)}"
        except Exception as e:
            return f"No direct path computed: {str(e)}"

chat_gds_service = ChatGDSService()
