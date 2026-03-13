from neo4j import AsyncGraphDatabase
import os
import re
from typing import List, Dict, Any, Optional
from app.logging_utils import db_logger

class Neo4jService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    def slugify_folder(self, name: str) -> str:
        """Standardized slugification matching seed_db.py."""
        return re.sub(r'[\W_]+', '_', name).upper()

    async def verify_connectivity(self):
        await self.driver.verify_connectivity()

    async def close(self):
        await self.driver.close()

    async def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Execute a read query using a retriable transaction function.
        Best practice for production environments.
        """
        async def _read_tx(tx):
            result = await tx.run(query, parameters or {})
            records = await result.data()
            return records

        try:
            async with self.driver.session() as session:
                return await session.execute_read(_read_tx)
        except Exception as e:
            db_logger.error(f"Neo4j read query failed: {e}")
            return []

    async def setup_constraints(self):
        """Pre-configure Neo4j with uniqueness constraints for performance and integrity."""
        db_logger.info("Configuring Neo4j indices and constraints...")
        # Constraint on base label for global ID lookup
        await self.execute_cypher("CREATE CONSTRAINT nexus_node_id IF NOT EXISTS FOR (n:NexusNode) REQUIRE n.id IS UNIQUE")
        # Indices for common search properties
        await self.execute_cypher("CREATE INDEX node_name_idx IF NOT EXISTS FOR (n:NexusNode) ON (n.name)")
        db_logger.info("Neo4j constraints configured.")

    async def get_schema_info(self):
        """Get full schema info — labels, properties, relationships, counts."""
        labels = await self.run_query("CALL db.labels() YIELD label RETURN label")
        rels = await self.run_query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        
        node_props = await self.run_query("""
            CALL db.schema.nodeTypeProperties() 
            YIELD nodeType, propertyName 
            RETURN nodeType, collect(propertyName) as properties
        """)
        
        rel_props = await self.run_query("""
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

    async def get_label_counts(self):
        """Get counts for all labels using a standard loop (avoiding APOC dependency)."""
        labels_raw = await self.run_query("CALL db.labels() YIELD label RETURN label")
        if not labels_raw:
            return {}
            
        counts = {}
        for l in labels_raw:
            label = l["label"]
            # Fast count using COUNT {} subquery if supported, else MATCH
            count_res = await self.run_query(f"MATCH (n:`{label}`) RETURN count(n) as count")
            if count_res:
                counts[label] = count_res[0]["count"]
        return counts

    async def execute_cypher(self, cypher: str):
        """Execute multiple Cypher statements using a retriable write transaction."""
        statements = [s.strip() for s in cypher.split(";") if s.strip()]
        
        async def _write_tx(tx):
            tx_results = []
            for statement in statements:
                res = await tx.run(statement)
                consume_res = await res.consume()
                tx_results.append(consume_res.counters.__dict__)
            return tx_results

        try:
            async with self.driver.session() as session:
                final_results = await session.execute_write(_write_tx)
                return {"results": final_results, "statement_count": len(statements)}
        except Exception as e:
            db_logger.error(f"Neo4j execute_cypher failed: {e}")
            return {"results": [], "statement_count": 0}

    async def execute_cypher_scoped(self, cypher: str, folder_id: str):
        """
        Execute Cypher while enforcing Native Label Scoping and NexusNode base label.
        """
        folder_label = f"Folder_{folder_id}"
        # Inject labels into node patterns (e.g., (n:Herb))
        scoped_cypher = re.sub(r'\(([\w\d]+)(:[\w\d:]+)?', r'(\1\2:NexusNode:`' + folder_label + '`', cypher)
        return await self.execute_cypher(scoped_cypher)

    async def get_full_graph_bidirectional(self, limit_nodes: int = 500, limit_rels: int = 1000, folder_slug: Optional[str] = None):
        """Fetch graph data with elementId and symmetric relationship collapsing."""
        label_filter = f":Folder_{folder_slug}" if folder_slug else ""
        
        nodes_res = await self.run_query(f"""
            MATCH (n{label_filter}) 
            RETURN elementId(n) AS id, labels(n)[0] AS label, coalesce(n['name'], n['id'], 'Unnamed') AS name, properties(n) AS properties 
            LIMIT {limit_nodes}
        """)
        
        rel_query = f"MATCH (a{label_filter})-[r]->(b{label_filter}) RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS type, properties(r) AS properties, elementId(r) AS id LIMIT {limit_rels}"
        rels_res = await self.run_query(rel_query)
        
        processed_rels = []
        seen_pairs = set()

        for rel in rels_res:
            s, t, rtype = rel['source'], rel['target'], rel['type']
            pair = tuple(sorted([s, t])) + (rtype,)
            
            if pair in seen_pairs:
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

    async def get_folder_node_counts(self):
        """Get node counts for all folders using efficient partial label scan."""
        query = """
        MATCH (n)
        UNWIND labels(n) as label
        WITH label WHERE label STARTS WITH 'Folder_'
        RETURN label, count(*) as count
        """
        results = await self.run_query(query)
        res_counts = {r['label'].replace("Folder_", ""): r['count'] for r in results}
        return res_counts

    async def merge_entities_with_guardian(self, nodes: List[Dict], relationships: List[Dict], folder_id: str):
        """Ingest nodes and relationships with label scoping inside a single transaction function."""
        folder_label = f"Folder_{folder_id}"
        
        async def _ingest_tx(tx):
            for node in nodes:
                # Merge on base labels and ID
                q = f"MERGE (n:NexusNode:`{node['label']}`:`{folder_label}` {{id: $id}}) SET n += $props"
                await tx.run(q, id=node['id'], props=node.get('properties', {}))
            
            for rel in relationships:
                is_sym = rel.get('properties', {}).get('isSymmetric', False)
                if is_sym:
                    # Direct check to prevent duplicates in symmetric sets
                    check_q = f"MATCH (a:`{folder_label}` {{id: $t}})-[r:`{rel['type']}`]-(b:`{folder_label}` {{id: $s}}) RETURN r"
                    chk = await tx.run(check_q, s=rel['source'], t=rel['target'])
                    if await chk.peek(): continue
                
                # Directed merge
                q = f"""
                MATCH (a:`{folder_label}` {{id: $s}}), (b:`{folder_label}` {{id: $t}}) 
                MERGE (a)-[r:`{rel['type']}`]->(b) 
                SET r += $props
                """
                await tx.run(q, s=rel['source'], t=rel['target'], props=rel.get('properties', {}))

        try:
            async with self.driver.session() as session:
                await session.execute_write(_ingest_tx)
        except Exception as e:
            db_logger.error(f"Symmetry Guardian ingestion failed: {e}")

    async def process_embeddings_batch(self, folder_id: Optional[str] = None):
        """Asynchronously processes nodes missing embeddings in batches."""
        from app.services.gemini_service import gemini_service
        import asyncio
        batch_size = 500
        folder_match = f":Folder_{folder_id}" if folder_id else ""
        
        while True:
            # elementId usage for precision
            query = f"""
            MATCH (n{folder_match}) 
            WHERE n['embedding'] IS NULL AND n['name'] IS NOT NULL
            RETURN elementId(n) as node_id, coalesce(n['name'], '') + ' ' + coalesce(n['description'], '') as text
            LIMIT {batch_size}
            """
            batch_nodes = await self.run_query(query)
            if not batch_nodes or not isinstance(batch_nodes, list): break
                
            embeddings = await gemini_service.generate_embeddings_batch([n['text'] for n in batch_nodes])
            if not embeddings: break
                
            updates = [{"id": batch_nodes[i]['node_id'], "emb": embeddings[i]} for i in range(len(batch_nodes))]
            await self.run_query("UNWIND $upd AS row MATCH (n) WHERE elementId(n) = row.id SET n.embedding = row.emb", {"upd": updates})
            await asyncio.sleep(1)

neo4j_service = Neo4jService()
