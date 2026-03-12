from neo4j import GraphDatabase
import os
from typing import List, Dict, Any
from app.logging_utils import db_logger

class Neo4jService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def slugify_folder(self, name: str) -> str:
        """Standardized slugification matching seed_db.py."""
        import re
        return re.sub(r'[\W_]+', '_', name).upper()

    def verify_connectivity(self):
        self.driver.verify_connectivity()

    def close(self):
        self.driver.close()

    def run_query(self, query: str, parameters: Dict[str, Any] = None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def get_schema_info(self):
        """Get full schema info — labels, properties, relationships, counts."""
        labels = self.run_query("CALL db.labels() YIELD label RETURN label")
        rels = self.run_query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        
        node_props = self.run_query("""
            CALL db.schema.nodeTypeProperties() 
            YIELD nodeType, propertyName 
            RETURN nodeType, collect(propertyName) as properties
        """)
        
        rel_props = self.run_query("""
            CALL db.schema.relTypeProperties() 
            YIELD relType, propertyName 
            RETURN relType, collect(propertyName) as properties
        """)

        return {
            "labels": [l["label"] for l in labels],
            "relationships": [r["relationshipType"] for r in rels],
            "node_properties": {p["nodeType"]: p["properties"] for p in node_props},
            "relationship_properties": {p["relType"]: p["properties"] for p in rel_props}
        }

    def get_label_counts(self):
        query = "CALL db.labels() YIELD label CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) YIELD value RETURN label, value.count as count"
        # Fallback if APOC is not available
        try:
            return {r["label"]: r["count"] for r in self.run_query(query)}
        except:
            labels = self.run_query("CALL db.labels() YIELD label RETURN label")
            counts = {}
            for l in labels:
                label = l["label"]
                count_res = self.run_query(f"MATCH (n:`{label}`) RETURN count(n) as count")
                counts[label] = count_res[0]["count"]
            return counts

    def execute_cypher(self, cypher: str):
        """Execute multiple Cypher statements separated by semicolons."""
        statements = [s.strip() for s in cypher.split(";") if s.strip()]
        results = []
        with self.driver.session() as session:
            for statement in statements:
                res = session.run(statement)
                results.append(res.consume().counters.__dict__)
        return {"results": results, "statement_count": len(statements)}

    def get_full_graph_bidirectional(self, limit_nodes=500, limit_rels=1000, folder_slug: str = None):
        """Fetch graph data and collapse symmetric relationships. Supports label-based isolation."""
        label_filter = f":Folder_{folder_slug}" if folder_slug else ""
        
        nodes_res = self.run_query(f"MATCH (n{label_filter}) RETURN elementId(n) AS id, labels(n)[0] AS label, coalesce(n.name, n.id, 'Unnamed') AS name, properties(n) AS properties LIMIT {limit_nodes}")
        
        # Fetch relationships — ensure they are linked to filtered nodes
        rel_query = f"MATCH (a{label_filter})-[r]->(b{label_filter}) RETURN elementId(a) AS source_id, elementId(b) AS target_id, type(r) AS type, properties(r) AS properties, elementId(r) AS id LIMIT {limit_rels}"
        rels_res = self.run_query(rel_query)
        
        processed_rels = []
        seen_pairs = set()

        for rel in rels_res:
            s, t, rtype = rel['source_id'], rel['target_id'], rel['type']
            # Create a sorted pair key to identify reverse edges
            pair = tuple(sorted([s, t])) + (rtype,)
            
            if pair in seen_pairs:
                # If we've seen this pair and type before, mark the existing one as symmetric
                for p_rel in processed_rels:
                    if (tuple(sorted([p_rel['source'], p_rel['target']])) + (p_rel['type'],)) == pair:
                        p_rel['isSymmetric'] = True
                        break
                continue
            
            seen_pairs.add(pair)
            processed_rels.append({
                "id": rel['id'],
                "source": s,
                "target": t,
                "type": rtype,
                "properties": rel['properties'],
                "isSymmetric": rel['properties'].get('isSymmetric', False)
            })

        return {"nodes": nodes_res, "relationships": processed_rels}

    def get_folder_node_counts(self):
        """Get node counts for all folders by scanning Folder_ labels."""
        query = """
        MATCH (n)
        UNWIND labels(n) as label
        WITH label WHERE label STARTS WITH 'Folder_'
        RETURN label, count(*) as count
        """
        results = self.run_query(query)
        # Convert List[Dict] to Dict { "folder_id": count }
        counts = {}
        for r in results:
            fid = r['label'].replace("Folder_", "")
            counts[fid] = r['count']
        return counts

    # Symmetry Guardian methods ported from old utils
    async def merge_entities_with_guardian(self, nodes: List[Dict], relationships: List[Dict], folder_id: str):
        folder_label = f"Folder_{folder_id}"
        with self.driver.session() as session:
            for node in nodes:
                session.execute_write(self._create_node_tx, node, folder_label)
            for rel in relationships:
                session.execute_write(self._create_rel_tx, rel, folder_label)

    @staticmethod
    def _create_node_tx(tx, node, folder_label):
        query = f"MERGE (n:`{node['label']}` {{id: $id}}) SET n += $properties SET n:`{folder_label}`"
        tx.run(query, id=node['id'], properties=node.get('properties', {}))

    @staticmethod
    def _create_rel_tx(tx, rel, folder_label):
        is_symmetric = rel.get('properties', {}).get('isSymmetric', False)
        if is_symmetric:
            check_query = f"MATCH (a {{id: $target}})-[r:`{rel['type']}`]-(b {{id: $source}}) RETURN r"
            result = tx.run(check_query, source=rel['source'], target=rel['target'])
            if result.peek(): return
        query = f"MATCH (a {{id: $source}}), (b {{id: $target}}) MERGE (a)-[r:`{rel['type']}`]->(b) SET r += $properties"
        tx.run(query, source=rel['source'], target=rel['target'], properties=rel.get('properties', {}))

    async def process_embeddings_batch(self, folder_id: str = None):
        """Asynchronously processes nodes missing embeddings in batches. Can be restricted to a folder."""
        from app.services.gemini_service import gemini_service
        import asyncio
        batch_size = 500
        
        db_logger.info(f"Starting background embedding pipeline for folder: {folder_id or 'ALL'}")
        
        folder_match = f":Folder_{folder_id}" if folder_id else ""
        
        while True:
            # Fetch nodes missing embeddings
            query = f"""
            MATCH (n{folder_match}) 
            WHERE n.embedding IS NULL AND n.name IS NOT NULL
            RETURN id(n) as node_id, coalesce(n.name, '') + ' ' + coalesce(n.description, '') as text_to_embed
            LIMIT {batch_size}
            """
            nodes = self.run_query(query)
            if not nodes:
                db_logger.info("All eligible nodes embedded successfully.")
                break
                
            db_logger.info(f"Processing embedding batch of {len(nodes)} nodes...")
            texts = [n['text_to_embed'] for n in nodes]
            embeddings = await gemini_service.generate_embeddings_batch(texts)
            
            if not embeddings or len(embeddings) != len(nodes):
                db_logger.error("Failed to generate complete embeddings. Aborting batch loop.")
                break
                
            updates = [{"id": nodes[i]['node_id'], "embedding": embeddings[i]} for i in range(len(nodes))]
            
            update_query = """
            UNWIND $updates AS row
            MATCH (n) WHERE id(n) = row.id
            SET n.embedding = row.embedding
            """
            self.run_query(update_query, {"updates": updates})
            db_logger.info(f"Successfully saved {len(updates)} embeddings to Neo4j.")
            await asyncio.sleep(2) # Prevent Gemini API rate limit throttling

neo4j_service = Neo4jService()
