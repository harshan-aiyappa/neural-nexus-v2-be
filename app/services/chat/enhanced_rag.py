import json
import asyncio
import re
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from app.services.neo4j_service import neo4j_service
from app.services.ollama_service import ollama_service
from app.services.gds_service import gds_service
from app.services.chat.prompts import get_enhanced_rag_system_prompt
from langchain_core.messages import BaseMessage
from app.logging_utils import ai_logger as logger

class RAGState(TypedDict):
    query: str
    folder_slug: Optional[str]
    history: List[BaseMessage]
    
    # Internal state
    cypher_query: str
    cypher_context: str
    vector_context: str
    gds_context: str
    built_context: str
    answer: str
    search_mode: str
    grounding_score: float

class EnhancedRAGService:
    def __init__(self):
        self._schema_cache = None
        self._schema_text_cache = None
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(RAGState)

        builder.add_node("introspect", self._introspect_node)
        builder.add_node("generate_cypher", self._generate_cypher_node)
        builder.add_node("execute_cypher", self._execute_cypher_node)
        builder.add_node("gds_enrich", self._gds_enrichment_node)
        builder.add_node("vector_search", self._vector_search_node)
        builder.add_node("synthesize", self._synthesize_node)
        builder.add_node("persist", self._persistence_node)

        builder.set_entry_point("introspect")
        builder.add_edge("introspect", "generate_cypher")
        builder.add_edge("generate_cypher", "execute_cypher")
        builder.add_edge("execute_cypher", "vector_search")
        builder.add_edge("vector_search", "gds_enrich")
        builder.add_edge("gds_enrich", "synthesize")
        builder.add_edge("synthesize", "persist")
        builder.add_edge("persist", END)


        return builder.compile()

    async def _get_schema_text(self) -> str:
        if self._schema_text_cache:
            return self._schema_text_cache
            
        try:
            schema = await neo4j_service.get_schema_info()
            if not schema:
                return "Schema unavailable."
            
            self._schema_cache = schema
            text = "NODE TYPES AND PROPERTIES:\n"
            
            labels = schema.get("labels") or []
            for label in labels:
                if label.startswith("Folder_") or label in ("NexusNode", "ChatMessage"): continue
                text += f"\n  :{label}\n"
                
                all_props = schema.get("node_properties") or {}
                props = all_props.get(label) or []
                for p in props:
                    if p not in ("embedding", "vector"):
                        text += f"    - {p}\n"
                        
            text += "\nRELATIONSHIP PATTERNS:\n"
            triplets = schema.get("triplets") or []
            for triplet in triplets:
                text += f"  (:{triplet.get('start')})-[:{triplet.get('type')}]->(:{triplet.get('end')})\n"
                
            self._schema_text_cache = text
            return text
        except Exception as e:
            logger.error(f"Failed to fetch schema for RAG: {e}")
            return "Schema unavailable."

    async def _introspect_node(self, state: RAGState):
        """Prepare context by ensuring schema is loaded."""
        await self._get_schema_text()
        return {}

    async def _generate_cypher_node(self, state: RAGState):
        schema_text = await self._get_schema_text()
        slug = state.get('folder_slug')
        
        folder_restriction = f"CRITICAL: ALL nodes in the query MUST have the label :`Folder_{slug}`. Note the backticks are REQUIRED for labels with hyphens. Example: MATCH (n:Herb:`Folder_{slug}`) " if slug else ""
        
        system_prompt = "You are a Neo4j Cypher expert for scientific knowledge graphs. Generate ONLY raw Cypher. No markdown, no comments."
        user_prompt = f"""
DATABASE SCHEMA:
{schema_text}

USER QUESTION: {state['query']}

RULES:
1. Return results as plain names and relationship types.
2. {folder_restriction}
3. Use toLower() for string comparisons.
4. ONLY USE properties that are VISIBLE in the SCHEMA below. Do NOT guess properties like 'formula' or 'weight' unless listed.
5. Limit to 15 results.
6. If the question is a greeting or general chat, return "NONE".

CYPHER QUERY:"""
        
        try:
            cypher = await ollama_service.generate_response(user_prompt=user_prompt, system_prompt=system_prompt)
            cypher = cypher.strip().replace("```cypher", "").replace("```", "").strip()
            
            if "NONE" in cypher.upper() or not any(x in cypher.upper() for x in ["MATCH", "CALL", "WITH"]):
                cypher = ""
                
            logger.info(f"[RAG] Generated Cypher: {cypher}")
            return {"cypher_query": cypher}
        except Exception as e:
            logger.error(f"Cypher generation failed: {e}")
            return {"cypher_query": ""}

    async def _execute_cypher_node(self, state: RAGState):
        cypher = state.get("cypher_query", "")
        if not cypher:
            return {"cypher_context": ""}
            
        try:
            results = await neo4j_service.run_query(cypher)
            if not results:
                return {"cypher_context": "No direct graph matches found."}
                
            context = "GRAPH DATABASE RESULTS:\n"
            for i, row in enumerate(results[:15]):
                row_str = ", ".join([f"{k}: {v}" for k, v in row.items() if v is not None])
                context += f"{i+1}. {row_str}\n"
            return {"cypher_context": context}
        except Exception as e:
            logger.error(f"Cypher execution error: {e}")
            return {"cypher_context": ""}

    async def _vector_search_node(self, state: RAGState):
        """Perform hybrid vector/keyword search for nodes."""
        query = state['query']
        slug = state.get('folder_slug')
        folder_filter = f":`Folder_{slug}`" if slug else ""
        
        context = ""
        try:
            # 1. Attempt Vector Search if embeddings available
            embedding = await ollama_service.generate_embeddings(query)
            if embedding:
                vector_query = f"""
                MATCH (n{folder_filter})
                WHERE n.embedding IS NOT NULL
                WITH n, vector.similarity.cosine(n.embedding, $emb) AS score
                WHERE score > 0.7
                RETURN coalesce(n.name, n.id) as name, labels(n)[0] as type, n.description as desc, score
                ORDER BY score DESC
                LIMIT 5
                """
                vectors = await neo4j_service.run_query(vector_query, {"emb": embedding})
                if vectors:
                    context += "SEMANTICALLY RELATED ENTITIES:\n"
                    for v in vectors:
                        desc = v['desc'][:100] + "..." if v.get('desc') and len(v['desc']) > 100 else v.get('desc', 'No description')
                        context += f"- {v['name']} ({v['type']}): {desc} [Match: {round(v['score']*100)}%]\n"
            
            # 2. Fallback Lexical Search if context still thin
            if len(context) < 100:
                terms = [t.lower() for t in query.split() if len(t) > 3]
                if terms:
                    lexical_query = f"""
                    MATCH (n{folder_filter})
                    WHERE ANY(term IN $terms WHERE toLower(coalesce(n.name, '')) CONTAINS term)
                    RETURN coalesce(n.name, n.id) as name, labels(n)[0] as type
                    LIMIT 5
                    """
                    lexical = await neo4j_service.run_query(lexical_query, {"terms": terms})
                    if lexical:
                        context += "\nKEYWORD MATCHES:\n"
                        for l in lexical:
                            context += f"- Found entity: {l['name']} ({l['type']})\n"
                            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            
        return {"vector_context": context}

    async def _gds_enrichment_node(self, state: RAGState):
        """Add graph analytics context based on query intent."""
        query = state['query'].lower()
        slug = state.get('folder_slug')
        context = ""
        
        try:
            # Detection of analytical intent
            if any(w in query for w in ["similar", "related", "like", "compare"]):
                sims = await gds_service.get_similarity(slug)
                if sims:
                    context += "PHYTOMERICAL SIMILARITY ANALYTICS:\n"
                    for s in sims[:3]:
                        context += f"- {s['herb1']} shares chemical markers with {s['herb2']} ({s['score']}% overlap).\n"
            
            if any(w in query for w in ["important", "central", "main", "hub", "influential"]):
                hubs = await gds_service.get_pagerank(slug)
                if hubs:
                    context += "\nNETWORK CENTRALITY (INFLUENCE):\n"
                    for h in hubs[:5]:
                        context += f"- {h['name']} ({h['type']}) is a high-influence hub [Score: {h['score']}].\n"
                        
            if any(w in query for w in ["group", "cluster", "community", "category"]):
                comms = await gds_service.get_communities(slug)
                if comms:
                    context += "\nCOMMUNITY CLUSTERS (SHARED PATHS):\n"
                    for c in comms[:3]:
                        context += f"- Cluster {c['community']}: {', '.join(c['nodes'][:5])}...\n"
                        
        except Exception as e:
            logger.error(f"GDS Enrichment failed: {e}")
            
        return {"gds_context": context}

    async def _synthesize_node(self, state: RAGState):
        """Generate final response from all combined contexts."""
        combined_context = f"""
{state.get('cypher_context', '')}
{state.get('vector_context', '')}
{state.get('gds_context', '')}
""".strip()

        if not combined_context:
            answer = "I'm sorry, I couldn't find any specific information in the knowledge graph for your request. Could you try rephrasing or asking about a different topic?"
            return {"answer": answer, "grounding_score": 0.0, "search_mode": "fallback"}

        system_prompt = get_enhanced_rag_system_prompt()
        user_prompt = f"""
CONTEXT FROM KNOWLEDGE GRAPH:
{combined_context}

USER QUERY: {state['query']}

(Respond ONLY based on context. If context doesn't answer it, state what you DO see.)
"""
        try:
            answer = await ollama_service.generate_response(user_prompt=user_prompt, system_prompt=system_prompt)
            return {"answer": answer, "grounding_score": 1.0, "search_mode": "hybrid_advanced", "built_context": combined_context}
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {"answer": "Error generating response.", "grounding_score": 0.0}

    async def _persistence_node(self, state: RAGState):
        """Asynchronously save the chat session for long-term memory."""
        from datetime import datetime
        try:
            # 1. Prepare data
            text_to_embed = f"User: {state['query']}\nAI: {state['answer']}"
            embedding = await ollama_service.generate_embeddings(text_to_embed)
            
            chat_data = {
                "message": state['query'],
                "response": state['answer'],
                "embedding": embedding,
                "folder_slug": state.get('folder_slug'),
                "timestamp": datetime.utcnow().isoformat(),
                "mentions": [] # Could be extracted from context if needed
            }
            
            # 2. Parallel Persistence
            from app.db.mongo_utils import mongo_service
            await asyncio.gather(
                mongo_service.save_chat_message(chat_data),
                neo4j_service.save_chat_as_node(chat_data)
            )
            logger.info("[RAG] Chat persisted to Dual-Storage.")
        except Exception as e:
            logger.error(f"Persistence failed: {e}")
        return {}

    async def chat(self, user_query: str, folder_slug: Optional[str] = None, history: List[BaseMessage] = []):
        initial_state = {
            "query": user_query,
            "folder_slug": folder_slug,
            "history": history,
            "cypher_query": "",
            "cypher_context": "",
            "vector_context": "",
            "gds_context": "",
            "built_context": "",
            "answer": "",
            "search_mode": "",
            "grounding_score": 0.0
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        return {
            "answer": final_state.get("answer"),
            "context": [final_state.get("built_context", "")],
            "grounding_score": final_state.get("grounding_score")
        }

enhanced_rag_service = EnhancedRAGService()
