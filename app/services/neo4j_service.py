from neo4j import AsyncGraphDatabase
import os
import time
import re
from typing import List, Dict, Any, Optional
from app.logging_utils import db_logger

class Neo4jService:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

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

    async def run_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a write query using a retriable transaction function."""
        async def _write_tx(tx):
            result = await tx.run(query, parameters or {})
            return await result.data()

        try:
            async with self.driver.session() as session:
                return await session.execute_write(_write_tx)
        except Exception as e:
            db_logger.error(f"Neo4j write query failed: {e}")
            return []

    async def setup_constraints(self):
        """Pre-configure Neo4j with uniqueness constraints for performance and integrity."""
        db_logger.info("Configuring Neo4j indices and constraints...")
        # Constraint on base label for global ID lookup
        await self.execute_cypher("CREATE CONSTRAINT therapeutic_use_id IF NOT EXISTS FOR (n:TherapeuticUse) REQUIRE n.id IS UNIQUE")
        # Indices for common search properties
        await self.execute_cypher("CREATE INDEX therapeutic_use_name_idx IF NOT EXISTS FOR (n:TherapeuticUse) ON (n.name)")
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
        # Strip comments and split by semicolon
        clean_cypher = re.sub(r'//.*', '', cypher)
        statements = [s.strip() for s in clean_cypher.split(";") if s.strip()]
        
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

    def slugify_folder(self, name: str) -> str:
        """Create a URL-safe slug from a folder name."""
        return name.lower().strip().replace(" ", "-").replace("_", "-")

    async def execute_cypher_scoped(self, cypher: str, folder_id: str):
        """
        Execute Cypher while enforcing Native Label Scoping and TherapeuticUse base label.
        Refined regex to only inject into patterns that don't satisfy TherapeuticUse logic yet.
        """
        folder_label = f"Folder_{folder_id}"
        # Only inject if the node pattern has a colon but NO TherapeuticUse yet
        # e.g., (n:Herb) -> (n:Herb:TherapeuticUse:`Folder_123`)
        # This avoid re-declaring variables like (h) which was causing syntax errors.
        scoped_cypher = re.sub(
            r'\(([\w\d]+):([\w\d:]+)', 
            r'(\1:\2:TherapeuticUse:`' + folder_label + '`', 
            cypher
        )
        return await self.execute_cypher(scoped_cypher)

    async def get_full_graph_bidirectional(self, limit_nodes: int = 500, limit_rels: int = 1000, folder_id: Optional[str] = None):
        """Fetch graph data with elementId and symmetric relationship collapsing."""
        # Use backticks to handle hyphens and IDs
        label_filter = f":`Folder_{folder_id}`" if folder_id else ""
        
        nodes_res = await self.run_query(f"""
            MATCH (n{label_filter}) 
            RETURN elementId(n) AS id, labels(n)[0] AS label, coalesce(n['name'], n['scientific_name'], n['common_name'], n['id'], 'Unnamed') AS name, properties(n) AS properties 
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

    async def get_neighbors(self, node_id: str, folder_id: Optional[str] = None):
        """Fetch immediate neighbors of a specific node."""
        folder_label = f"Folder_{folder_id}" if folder_id else None
        
        # Base query to fetch neighbors
        # We use OPTIONAL MATCH to ensure we get something even if no neighbors exist (though usually redundant for expansion)
        query = """
        MATCH (n)-[r]-(m)
        WHERE elementId(n) = $node_id
        RETURN 
            elementId(m) AS id, 
            labels(m)[0] AS label, 
            labels(m) AS all_labels,
            coalesce(m['name'], m['scientific_name'], m['common_name'], m['id'], 'Unnamed') AS name, 
            properties(m) AS properties,
            elementId(m) AS m_id,
            elementId(n) AS n_id,
            type(r) AS rel_type,
            properties(r) AS rel_props,
            elementId(r) AS rel_id
        """
        results = await self.run_query(query, {"node_id": node_id})
        
        nodes = []
        relationships = []
        seen_node_ids = {node_id} 
        
        for record in results:
            m_id = record['id']
            
            # If folder scoping is active, only include nodes that belong to the folder
            if folder_label and folder_label not in record['all_labels']:
                continue

            if m_id not in seen_node_ids:
                nodes.append({
                    "id": m_id,
                    "label": record['label'],
                    "name": record['name'],
                    "properties": record['properties']
                })
                seen_node_ids.add(m_id)
            
            relationships.append({
                "id": record['rel_id'],
                "source": record['n_id'],
                "target": record['m_id'],
                "type": record['rel_type'],
                "properties": record['rel_props'],
                "isSymmetric": record['rel_props'].get('isSymmetric', False)
            })
            
        return {"nodes": nodes, "relationships": relationships}

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
                q = f"MERGE (n:TherapeuticUse:`{node['label']}`:`{folder_label}` {{id: $id}}) SET n += $props"
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
        batch_size = 200
        folder_match = f":Folder_{folder_id}" if folder_id else ""
        
        while True:
            # elementId usage for precision
            query = f"""
            MATCH (n{folder_match}) 
            WHERE n['embedding'] IS NULL AND n['name'] IS NOT NULL
            RETURN elementId(n) as node_id, coalesce(n['name'], '') + ' ' + coalesce(n['description'], '') as text
            LIMIT {batch_size}
            """
            batch_nodes = await self.run_write_query(query)
            if not batch_nodes or not isinstance(batch_nodes, list): break
                
            embeddings = await gemini_service.generate_embeddings_batch([n['text'] for n in batch_nodes])
            if not embeddings: break
                
            updates = [{"id": batch_nodes[i]['node_id'], "emb": embeddings[i]} for i in range(len(batch_nodes))]
            await self.run_write_query("UNWIND $upd AS row MATCH (n) WHERE elementId(n) = row.id SET n.embedding = row.emb", {"upd": updates})
            await asyncio.sleep(1)

    async def save_chat_as_node(self, chat_data: Dict):
        """Store chat as a node and link to topic/folder."""
        node_id = f"chat_{time.time()}"
        folder_label = f"Folder_{chat_data.get('folder_slug')}" if chat_data.get('folder_slug') else None
        
        async def _persist_tx(tx):
            # 1. Create ChatMessage node
            q = "CREATE (c:ChatMessage {id: $id, text: $text, response: $response, embedding: $emb, timestamp: $ts})"
            await tx.run(q, id=node_id, text=chat_data['message'], response=chat_data['response'], emb=chat_data.get('embedding'), ts=chat_data.get('timestamp'))
            
            # 2. Link to Folder if available
            if folder_label:
                link_folder_q = f"MATCH (c:ChatMessage {{id: $id}}), (f:`{folder_label}`) MERGE (c)-[:FOR_TOPIC]->(f)"
                await tx.run(link_folder_q, id=node_id)
            
            # 3. Link to mentioned entities (Simple approach: if IDs are in mentions list)
            mentions = chat_data.get('mentions', [])
            for m_id in mentions:
                link_entity_q = "MATCH (c:ChatMessage {id: $id}), (e) WHERE elementId(e) = $m_id MERGE (c)-[:MENTIONS]->(e)"
                await tx.run(link_entity_q, id=node_id, m_id=m_id)

        try:
            async with self.driver.session() as session:
                await session.execute_write(_persist_tx)
        except Exception as e:
            db_logger.error(f"Neo4j chat persistence failed: {e}")

neo4j_service = Neo4jService()
