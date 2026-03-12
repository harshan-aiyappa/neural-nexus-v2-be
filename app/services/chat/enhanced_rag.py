import logging
import json
import asyncio
import time as _time
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from app.services.neo4j_service import neo4j_service
from app.services.gemini_service import gemini_service
from app.services.chat.prompts import get_enhanced_rag_system_prompt, get_greeting_prompt
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

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
        builder.add_node("retrieve", self._retrieval_node)
        builder.add_node("generate", self._generation_node)

        builder.set_entry_point("clarify")
        
        builder.add_conditional_edges(
            "clarify",
            lambda x: "end" if x.get("needs_clarification") else "continue",
            {"end": END, "continue": "retrieve"}
        )
        
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

    async def _retrieval_node(self, state: RAGState):
        """Fetch contextual data from Neo4j based on the folder slug."""
        slug = state.get('folder_slug')
        label_filter = f":Folder_{slug}" if slug else ""
        
        # Simple lexical/label-based search for now
        query = f"""
        MATCH (n{label_filter})
        WHERE toLower(toString(coalesce(n.name, n.id, elementId(n), ''))) CONTAINS toLower($term)
        OR toLower(toString(coalesce(n.description, ''))) CONTAINS toLower($term)
        RETURN coalesce(n.name, toString(n.id), elementId(n)) as name, coalesce(n.description, '') as description, labels(n)[0] as type
        LIMIT 10
        """
        results = neo4j_service.run_query(query, {"term": state['query']})
        
        context = []
        for r in results:
            context.append(f"• {r['name']} [{r['type']}]: {r['description']}")
            
        # Extend context with multi-hop undirected relationships (-[:REL*1..2]-)
        if results:
            # Fixing Directional Ignorance: Using Undirected Pathfinding (hop depth = 1 to 2)
            rel_query = f"""
            MATCH p = (n{label_filter})-[*1..2]-(m)
            WHERE n.name IN $names
            UNWIND relationships(p) as r
            WITH startNode(r) as s, type(r) as t, endNode(r) as d
            RETURN DISTINCT coalesce(s.name, s.id, 'Unknown') as source, 
                            t as type, 
                            coalesce(d.name, d.id, 'Unknown') as target
            LIMIT 50
            """
            names = [r['name'] for r in results]
            rels = neo4j_service.run_query(rel_query, {"names": names})
            for r in rels:
                context.append(f"Relationship: {r['source']} -[{r['type']}]-> {r['target']}")

        return {"context": context}

    async def _generation_node(self, state: RAGState):
        """Generate final answer using Gemini."""
        context_str = "\n".join(state.get('context', []))
        system_prompt = get_enhanced_rag_system_prompt()
        
        user_prompt = f"FOLDER CONTEXT: {state.get('folder_slug')}\n\nDATABASE EVIDENCE:\n{context_str}\n\nUSER QUESTION: {state['query']}"
        
        # Call Gemini (using the existing service)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Adapt history if available
        # ... logic for history ...

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
