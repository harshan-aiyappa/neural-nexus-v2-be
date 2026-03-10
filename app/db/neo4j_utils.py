from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

class Neo4jSymmetryGuardian:
    def __init__(self):
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    async def merge_entities_with_guardian(self, nodes: List[Dict], relationships: List[Dict], folder_id: str):
        """
        Implements the Global Master Standard:
        1. Native Labeling (:Folder_XYZ) for O(1) performance.
        2. Symmetry Guardian check for undirected relationships.
        """
        folder_label = f"Folder_{folder_id}"
        
        with self.driver.session() as session:
            # 1. Create Nodes with Native Folder Labels
            for node in nodes:
                session.execute_write(self._create_node_tx, node, folder_label)
            
            # 2. Create Relationships with Symmetry Guardian
            for rel in relationships:
                session.execute_write(self._create_rel_tx, rel, folder_label)

    @staticmethod
    def _create_node_tx(tx, node, folder_label):
        # Dynamically append the native folder label for fast retrieval
        query = f"""
        MERGE (n:{node['label']} {{id: $id}})
        SET n += $properties
        SET n:{folder_label}
        """
        tx.run(query, id=node['id'], properties=node.get('properties', {}))

    @staticmethod
    def _create_rel_tx(tx, rel, folder_label):
        # Symmetry Guardian Logic:
        # If isSymmetric is true, we ensure no duplicate inverse relationship exists
        # before creating the edge.
        
        is_symmetric = rel.get('properties', {}).get('isSymmetric', False)
        
        if is_symmetric:
            # Check for inverse relationship existence
            check_query = f"""
            MATCH (a {{id: $target}})-[r:{rel['type']}]-(b {{id: $source}})
            RETURN r
            """
            result = tx.run(check_query, source=rel['source'], target=rel['target'])
            if result.peek():
                return # Relationship already exists symmetrically
        
        # Merge relationship normally if not symmetric or if no inverse exists
        query = f"""
        MATCH (a {{id: $source}}), (b {{id: $target}})
        MERGE (a)-[r:{rel['type']}]->(b)
        SET r += $properties
        """
        tx.run(query, source=rel['source'], target=rel['target'], properties=rel.get('properties', {}))

db_guardian = Neo4jSymmetryGuardian()
