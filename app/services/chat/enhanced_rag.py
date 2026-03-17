import json
import asyncio
import re
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from app.services.neo4j_service import neo4j_service
from app.services.gemini_service import gemini_service
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

        builder.set_entry_point("introspect")
        builder.add_edge("introspect", "generate_cypher")
        builder.add_edge("generate_cypher", "execute_cypher")
        builder.add_edge("execute_cypher", "vector_search")
        builder.add_edge("vector_search", "gds_enrich")
        builder.add_edge("gds_enrich", "synthesize")
        builder.add_edge("synthesize", END)

        return builder.compile()

    async def _get_schema_text(self) -> str:
        if self._schema_text_cache:
            return self._schema_text_cache
            
        schema = await neo4j_service.get_schema_info()
        self._schema_cache = schema
        
        text = "NODE TYPES AND PROPERTIES:\n"
        for label in schema.get("labels", []):
            if label.startswith("Folder_") or label in ("NexusNode",): continue
            text += f"\n  :{label}\n"
            props = schema.get("node_properties", {}).get(label, [])
            if props:
                for p in props:
                    if p not in ("embedding",):
                        text += f"    - {p}\n"
                    
        text += "\nRELATIONSHIP PATTERNS:\n"
        for r in schema.get("relationships", []):
            text += f"  -[:{r}]->\n"
            
        self._schema_text_cache = text
        return text

    async def _introspect_node(self, state: RAGState):
        """Introspect Schema for Context generation."""
        await self._get_schema_text()
        return {}

    async def _generate_cypher_node(self, state: RAGState):
        schema_text = await self._get_schema_text()
        slug = state.get('folder_slug')
        
        # Scoping logic
        folder_instruction = f"CRITICAL: ALL nodes MATCHED MUST HAVE the label :Folder_{slug}. Example: MATCH (n:Herb:Folder_{slug})-[r]->(m:Folder_{slug})" if slug else ""
        
        prompt = f"""You are an expert Neo4j Cypher query generator.

DATABASE SCHEMA:
{schema_text}

CRITICAL RULES:
1. Generate ONLY the Cypher query. No explanations, no markdown.
2. {folder_instruction}
3. Use toLower() for ALL string comparisons. example: WHERE toLower(n.name) CONTAINS "abc"
4. Limit results to 20.
5. Return clean node names/properties, avoid returning raw nodes. Example: RETURN coalesce(a.name, a.id) as entity1, type(r) as rel, coalesce(b.name, b.id) as entity2

QUESTION: {state['query']}

CYPHER QUERY:"""
        
        try:
            cypher = await gemini_service.generate_response(user_prompt=prompt, system_prompt="Just return the cypher.")
            cypher = cypher.strip().replace("```cypher", "").replace("```", "").strip()
            
            if not cypher.upper().startswith(('MATCH', 'CALL', 'WITH')):
                cypher = ""
                
            logger.info(f"[CYPHER GENERATED] {cypher}")
            return {"cypher_query": cypher}
        except Exception as e:
            logger.error(f"Generate Cypher Error: {e}")
            return {"cypher_query": ""}

    async def _execute_cypher_node(self, state: RAGState):
        cypher = state.get("cypher_query", "")
        cypher_context = ""
        
        if cypher:
            try:
                # Add folder scope stringently if it's missed
                slug = state.get("folder_slug")
                if slug and f":Folder_{slug}" not in cypher:
                    pass # Just run it directly
                         
                results = await neo4j_service.run_query(cypher)
                if results and isinstance(results, list):
                    cypher_context = "Graph Database Results:\n"
                    for i, row in enumerate(results[:20]):
                        parts = [f"{k}: {v}" for k, v in row.items() if v is not None]
                        cypher_context += f"  {i+1}. {', '.join(parts)}\n"
            except Exception as e:
                logger.error(f"Cypher execution failed: {e}")
                
        return {"cypher_context": cypher_context}

    async def _vector_search_node(self, state: RAGState):
        """Use simple fallback keyword search to simulate vector search if embeddings setup missing."""
        slug = state.get("folder_slug")
        label_filter = f":Folder_{slug}" if slug else ""
        query_text = state["query"]
        terms = [t for t in query_text.split() if len(t) > 3]
        
        context = ""
        if terms:
            try:
                # Fallback purely lexical
                anchor_query = f"""
                MATCH (n{label_filter})
                WHERE ANY(term IN $terms WHERE toLower(toString(coalesce(n.name, n.id, n.description, ''))) CONTAINS toLower(term))
                RETURN coalesce(n.name, n.id) as name, labels(n)[0] as type, coalesce(n.description, '') as desc
                LIMIT 5
                """
                anchors = await neo4j_service.run_query(anchor_query, {"terms": terms})
                if anchors:
                    context = "Semantically related semantic references:\n"
                    for r in anchors:
                        d = r['desc'][:120] + "..." if len(r['desc']) > 120 else r['desc']
                        context += f"  - [{r['type']}] {r['name']}: {d}\n"
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                
        return {"vector_context": context}

    async def _gds_enrichment_node(self, state: RAGState):
        q_lower = state['query'].lower()
        gds_context_parts = []
        slug = state.get("folder_slug")
        
        gds_intents = {
            "similarity": ["similar", "alike", "related", "comparable"],
            "community": ["cluster", "community", "group", "family"],
            "centrality": ["important", "influential", "most connected", "hub", "top", "main"]
        }
        
        detected_intents = []
        for intent, keywords in gds_intents.items():
            if any(kw in q_lower for kw in keywords):
                detected_intents.append(intent)
                
        try:
            if "similarity" in detected_intents:
                sims = await gds_service.get_similarity(slug)
                if sims:
                    lines = ["Top similar entities based on shared relationships:"]
                    for s in sims[:5]:
                        lines.append(f"- {s['herb1']} is similar to {s['herb2']} (Overlap Score: {s['score']}%)")
                    gds_context_parts.append("\n".join(lines))
                    
            if "community" in detected_intents:
                comms = await gds_service.get_communities(slug)
                if comms:
                    lines = ["Community clusters detected by shared paths:"]
                    for i, c in enumerate(comms[:3]):
                        names = ", ".join(c["nodes"][:8])
                        lines.append(f"  Cluster {c['community']} ({len(c['nodes'])} members): {names}")
                    gds_context_parts.append("\n".join(lines))
                    
            if "centrality" in detected_intents:
                ranks = await gds_service.get_pagerank(slug)
                if ranks:
                    lines = ["Most important entities (PageRank-like hub score):"]
                    for r in ranks[:5]:
                        score_val = r.get('score', 0)
                        lines.append(f"  - {r['name']} (Type: {r['type']}): Connection Score {score_val}")
                    gds_context_parts.append("\n".join(lines))
                    
        except Exception as e:
            logger.error(f"GDS Enrichment error: {e}")

        ctx = "\n\n".join(gds_context_parts)
        return {"gds_context": ctx}

    async def _synthesize_node(self, state: RAGState):
        q = state['query']
        slug = state.get("folder_slug")
        
        combined_context = ""
        if state.get("cypher_context"):
            combined_context += state["cypher_context"] + "\n\n"
        if state.get("vector_context"):
            combined_context += state["vector_context"] + "\n\n"
        if state.get("gds_context"):
            combined_context += "Graph Analytics (GDS):\n" + state["gds_context"] + "\n\n"
            
        sys_prompt = "You are an advanced researcher answering questions strictly from the provided Graph Database Context. Use Markdown. If context is empty, say so."
        user_prompt = f"FOLDER CONTEXT: {slug}\n\nUSER QUESTION: {q}\n\nKNOWLEDGE GRAPH CONTEXT:\n{combined_context}"
        
        if not combined_context.strip():
            answer = "I searched the knowledge graph using both Cypher queries and GDS analytics but found no matching results in this folder.\n\nTry rephrasing your question."
            score = 0.0
            search_mode = "no_results"
        else:
            answer = await gemini_service.generate_response(user_prompt, sys_prompt)
            score = 0.95
            search_mode = "hybrid_gds" if "Graph Analytics" in combined_context else "hybrid"
            
        return {"answer": answer, "built_context": combined_context, "grounding_score": score, "search_mode": search_mode}

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
