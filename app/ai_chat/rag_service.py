from app.ai_chat.gemini_service import chat_gemini_service
from app.ai_chat.embedding_service import chat_embedding_service
from app.ai_chat.gds_service import chat_gds_service
from app.services.neo4j_service import neo4j_service
import re
from app.logging_utils import ai_logger as logger

class ChatRAGService:
    def __init__(self):
        self._schema_cache = None
        self._schema_text_cache = None

    async def get_schema(self) -> dict:
        if self._schema_cache is None:
            self._schema_cache = await neo4j_service.get_schema_info()
        return self._schema_cache

    async def get_schema_text(self) -> str:
        if self._schema_text_cache:
            return self._schema_text_cache

        schema = await self.get_schema()
        text = "NODE TYPES AND PROPERTIES:\n"

        for label in schema.get("labels", []):
            if label.startswith("Folder_") or label == "NexusNode": continue
            text += f"\n  :{label}\n"
            props = schema["node_properties"].get(label, [])
            for p in props:
                if p != "embedding":
                    text += f"    - {p}\n"

        text += "\nKNOWN RELATIONSHIP PATHS:\n"
        for t in schema.get("triplets", []):
            text += f"  (:{t['start']})-[:{t['type']}]->(:{t['end']})\n"

        self._schema_text_cache = text
        return text

    async def generate_cypher(self, question: str, folder_slug: str = "") -> str:
        schema_text = await self.get_schema_text()
        
        folder_instruction = f"CRITICAL: ALL nodes MATCHED MUST HAVE the label :`Folder_{folder_slug}`. Example: MATCH (n:Herb:`Folder_{folder_slug}`)-[r]->(m:`Folder_{folder_slug}`)" if folder_slug else ""

        prompt = f"""You are an expert Neo4j Cypher query generator for complex biological and research data.

DATABASE SCHEMA:
{schema_text}

CRITICAL RULES:
1. Generate ONLY the Cypher query. No explanations, no markdown, no code blocks.
2. Use toLower() for STRING comparisons. Example: WHERE toLower(n.name) CONTAINS "abc"
3. Limit results to 50.
4. {folder_instruction}
5. DYNAMIC MULTI-HOP: If the user asks for a connection that requires multiple steps, ALWAY follow the path. 
   Example for "X connected to Y": MATCH (a)-[*1..3]->(b) WHERE ...
   Use specific labels from the schema if possible, but allow variable length paths if the exact relationship count is unknown.
6. TARGET SEARCH: If looking for "Herbs with specific effects", your query MUST traverse from the Herb to the effect via any intermediate entities (Phytochemicals, etc).
   Pattern: (h:Herb)-[*1..5]-(target)
7. RETURN clean columns: RETURN a.name as source, type(r) as rel, b.name as target, labels(a) as source_type, labels(b) as target_type

QUESTION: {question}

CYPHER QUERY:"""

        cypher = await chat_gemini_service.generate_with_config(prompt, temperature=0.1, max_tokens=1024)
        
        # Clean up
        cypher = cypher.strip()
        if cypher.startswith("```"):
            lines = cypher.split("\n")
            cypher = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        if cypher.lower().startswith("cypher\n"):
            cypher = cypher[7:].strip()
        if cypher.lower().startswith("cypher "):
            cypher = cypher[7:].strip()

        if not cypher.upper().startswith(('MATCH', 'CALL', 'WITH')):
            return ""

        return cypher

    async def answer(self, question: str, folder_slug: str = "") -> dict:
        logger.info(f"[Q] RAG Query: {question}")
        
        cypher_query = ""
        cypher_context = ""
        try:
            cypher_query = await self.generate_cypher(question, folder_slug)
            if cypher_query:
                logger.info(f"[CYP] Generated Cypher: {cypher_query}")
                results = await neo4j_service.run_query(cypher_query)
                if results:
                    cypher_context = "Graph database query results:\n"
                    for i, row in enumerate(results[:25]):
                        parts = [f"{k}: {v}" for k, v in row.items() if v is not None]
                        cypher_context += f"  {i+1}. {', '.join(parts)}\n"
        except Exception as e:
            logger.error(f"[WARN] Cypher error: {e}")

        # Vector context
        vector_context = ""
        vector_count = 0
        try:
            vector_results = await chat_embedding_service.vector_search(question, top_k=5, folder_id=folder_slug)
            vector_count = len(vector_results)
            if vector_results:
                vector_context = "Semantically related entities:\n"
                for r in vector_results:
                    score_pct = round(r.get("score", 0) * 100, 1)
                    desc = r.get("description", "No description") or ""
                    if len(desc) > 120:
                        desc = desc[:120] + "..."
                    vector_context += f"  - [{r.get('label', '')}] {r.get('name', 'Unknown')} ({score_pct}% match): {desc}\n"
        except Exception as e:
            logger.error(f"[WARN] Vector search error: {e}")

        # GDS context
        gds_context = ""
        q_lower = question.lower()
        gds_intents = {
            "similarity": ["similar", "alike", "related", "comparable"],
            "community": ["cluster", "community", "group", "family"],
            "centrality": ["important", "central", "influential", "hub", "top", "main"],
            "pathfinding": ["path between", "route", "connected to"]
        }

        detected_intents = []
        for intent, keywords in gds_intents.items():
            if any(kw in q_lower for kw in keywords):
                detected_intents.append(intent)

        if detected_intents:
            gds_parts = []
            if "similarity" in detected_intents:
                ctx = await chat_gds_service.get_similarity_context(folder_id=folder_slug)
                if ctx: gds_parts.append(ctx)
            if "community" in detected_intents:
                ctx = await chat_gds_service.get_community_context(folder_id=folder_slug)
                if ctx: gds_parts.append(ctx)
            if "centrality" in detected_intents:
                ctx = await chat_gds_service.get_centrality_context(folder_id=folder_slug)
                if ctx: gds_parts.append(ctx)
            if "pathfinding" in detected_intents:
                match = re.search(r'(?:between|from)\s+["\']?(\w[\w\s]*?)["\']?\s+(?:and|to)\s+["\']?(\w[\w\s]*?)["\']?(?:\s|$|\?)', question, re.IGNORECASE)
                if match:
                    e1, e2 = match.group(1).strip(), match.group(2).strip()
                    ctx = await chat_gds_service.get_path_context(e1, e2, folder_id=folder_slug)
                    if ctx: gds_parts.append(ctx)
            gds_context = "\n\n".join(gds_parts)

        # Mode
        has_cypher = bool(cypher_context)
        has_vector = bool(vector_context)

        if has_cypher and has_vector:
            search_mode = "hybrid_gds" if gds_context else "hybrid"
        elif has_cypher:
            search_mode = "cypher_only"
        elif has_vector:
            search_mode = "vector_only"
        else:
            search_mode = "no_results"

        # Final answer
        combined_context = ""
        if search_mode == "no_results":
            final_answer = "I searched the knowledge graph using both Cypher queries and semantic vector search but found no matching results.\n\nTry rephrasing your question."
        else:
            if cypher_context: combined_context += cypher_context + "\n"
            if vector_context: combined_context += vector_context + "\n"
            if gds_context: combined_context += f"Graph analytics:\n{gds_context}\n"

            answer_prompt = f"""You are a research assistant answering questions from a Neo4j knowledge graph.

A researcher asked: "{question}"

KNOWLEDGE GRAPH CONTEXT:
{combined_context}

INSTRUCTIONS:
- Answer comprehensively based ONLY on the above context
- Use markdown formatting with headers and bullet points
- Cite specific data from the results
- If context is insufficient, state what data might be missing
- Be scientifically accurate and concise"""
            final_answer = await chat_gemini_service.generate(answer_prompt)

        return {
            "answer": final_answer,
            "cypher_used": cypher_query,
            "gds_context": gds_context,
            "search_mode": search_mode,
            "vector_results": vector_count,
            "context": combined_context
        }

chat_rag_service = ChatRAGService()
