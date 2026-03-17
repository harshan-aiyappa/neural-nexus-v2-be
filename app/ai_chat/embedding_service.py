from sentence_transformers import SentenceTransformer
from app.services.neo4j_service import neo4j_service
import os
import numpy as np

EMBEDDING_DIMENSION = 384

class ChatEmbeddingService:
    def __init__(self):
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self._model = None
        self._model_name = model_name

    @property
    def model(self):
        if self._model is None:
            from app.logging_utils import ai_logger
            ai_logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def generate_embedding(self, text: str) -> list[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()

    async def vector_search(self, query_text: str, top_k: int = 5, folder_id: str = "") -> list[dict]:
        query_embedding = self.generate_embedding(query_text)
        all_results = []
        schema = await neo4j_service.get_schema_info()
        labels = schema.get("labels", [])

        # Skip administrative labels
        labels = [l for l in labels if not l.startswith("Folder_") and l != "NexusNode"]

        for label in labels:
            idx_name = f"vector_{label.lower()}"
            try:
                # If folder_id is provided, we still query by index, but we might want to filter
                # Neo4j GDS / Vector index query can return nodes, we can then post-filter them.
                query = f"""
                    CALL db.index.vector.queryNodes('{idx_name}', $top_k, $embedding)
                    YIELD node, score
                    WHERE score > 0.5
                """
                if folder_id:
                    query += f" AND 'Folder_{folder_id}' IN labels(node)"
                
                query += f"""
                    RETURN coalesce(node.name, node.common_name, node.scientific_name, node.id, 'Unknown') AS name,
                           '{label}' AS label,
                           node.description AS description,
                           score
                    ORDER BY score DESC
                """
                
                results = await neo4j_service.run_query(query, {"top_k": top_k, "embedding": query_embedding})
                all_results.extend(results)
            except Exception:
                pass

        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:top_k]

chat_embedding_service = ChatEmbeddingService()
