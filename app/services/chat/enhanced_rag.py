import json
import asyncio
import time as _time
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from app.services.neo4j_service import neo4j_service
from app.services.gemini_service import gemini_service
from app.services.chat.prompts import get_enhanced_rag_system_prompt, get_greeting_prompt
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from app.logging_utils import ai_logger as logger

class RAGState(TypedDict):
    query: str
    folder_slug: Optional[str]
    history: List[BaseMessage]
    
    # Internal state
    enhanced_query: str
    context: List[str]
    answer: str
    grounding_score: float
    citations: List[Dict[str, Any]]
    needs_clarification: bool
    clarification_question: str

class EnhancedRAGService:
    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(RAGState)

        builder.add_node("clarify", self._clarification_node)
        builder.add_node("expand", self._expansion_node)
        builder.add_node("retrieve", self._retrieval_node)
        builder.add_node("generate", self._generation_node)

        builder.set_entry_point("clarify")
        
        builder.add_conditional_edges(
            "clarify",
            lambda x: "end" if x.get("needs_clarification") else "continue",
            {"end": END, "continue": "expand"}
        )
        
        builder.add_edge("expand", "retrieve")
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", END)

        return builder.compile()

    async def _clarification_node(self, state: RAGState):
        """Check if the query is too vague."""
        q = state['query'].strip()
        if len(q.split()) < 2:
            suggest = "Could you be more specific? For example, ask about a specific person, project, or technology."
            return {"needs_clarification": True, "answer": suggest}
        return {"needs_clarification": False}

    async def _expansion_node(self, state: RAGState):
        """Expand user query into scientific terms using Gemini."""
        from app.services.chat.prompts import get_query_expansion_prompt
        
        prompt = get_query_expansion_prompt()
        user_input = f"User Query: {state['query']}"
        
        try:
            expansion_raw = await gemini_service.generate_response(user_input, prompt)
            # Clean JSON if Gemini wraps it in code blocks
            clean_json = expansion_raw.strip().replace("```json", "").replace("```", "").strip()
            terms = json.loads(clean_json)
            if not isinstance(terms, list): terms = [state['query']]
            logger.info(f"Expanded Query Terms: {terms}")
            return {"enhanced_query": ", ".join(terms)}
        except Exception as e:
            logger.warning(f"Query expansion failed: {e}. Using original query.")
            return {"enhanced_query": state['query']}

    async def _retrieval_node(self, state: RAGState):
        """Fetch contextual data from Neo4j with multi-hop undirected traversal."""
        slug = state.get('folder_slug')
        label_filter = f":Folder_{slug}" if slug else ""
        
        # 1. Broad Anchor Search (Lexical)
        raw_terms = state.get('enhanced_query') or state.get('query') or ""
        terms = str(raw_terms).split(", ")
        
        anchor_query = f"""
        MATCH (n{label_filter})
        WHERE ANY(term IN $terms WHERE toLower(toString(coalesce(n.name, n.id, ''))) CONTAINS toLower(term))
        RETURN DISTINCT n.id as id, coalesce(n.name, n.id) as name, labels(n)[0] as type
        LIMIT 10
        """
        anchors = await neo4j_service.run_query(anchor_query, {"terms": terms})
        
        if not anchors:
            return {"context": ["No direct matches found in the knowledge graph."]}

        anchor_ids = [a['id'] for a in anchors]
        
        # 2. Multi-Hop Undirected Traversal (Depth 1-2)
        rel_query = f"""
        MATCH p = (n{label_filter})-[*1..2]-(m)
        WHERE n.id IN $ids
        UNWIND relationships(p) as r
        WITH startNode(r) as s, type(r) as t, endNode(r) as d
        RETURN DISTINCT 
            coalesce(s.name, s.id) as source, 
            t as type, 
            coalesce(d.name, d.id) as target,
            labels(s)[0] as s_type,
            labels(d)[0] as d_type
        LIMIT 40
        """
        rels = await neo4j_service.run_query(rel_query, {"ids": anchor_ids})
        
        context: List[str] = []
        # Add basic info about anchor nodes
        for a in anchors:
            context.append(f"Entity: {a['name']} ({a['type']})")
            
        # Add relationship context
        for r in rels:
            context.append(f"Connection: {r['source']} ({r['s_type']}) -[{r['type']}]- {r['target']} ({r['d_type']})")

        logger.info(f"Retrieved {len(context)} context segments via multi-hop.")
        return {"context": context[:50]}

    async def _generation_node(self, state: RAGState):
        """Generate final answer using Gemini."""
        raw_context = state.get('context') or []
        context_list = list(raw_context) if isinstance(raw_context, (list, tuple)) else []
        context_str = "\n".join([str(c) for c in context_list])
        
        system_prompt = get_enhanced_rag_system_prompt()
        user_prompt = f"FOLDER CONTEXT: {state.get('folder_slug')}\n\nDATABASE EVIDENCE:\n{context_str}\n\nUSER QUESTION: {state['query']}"
        
        reply = await gemini_service.generate_response(user_prompt, system_prompt)
        
        # Simple grounding score calculation
        score = 0.95 if context_str else 0.5
        
        return {"answer": reply, "grounding_score": score}

    async def chat(self, user_query: str, folder_slug: Optional[str] = None, history: List[BaseMessage] = []):
        initial_state = {
            "query": user_query,
            "folder_slug": folder_slug,
            "history": history,
            "context": [],
            "answer": "",
            "grounding_score": 0.0,
            "citations": [],
            "needs_clarification": False
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state

# Singleton instance
enhanced_rag_service = EnhancedRAGService()
