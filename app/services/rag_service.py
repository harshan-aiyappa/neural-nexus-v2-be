import os
from typing import Annotated, TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from neo4j import GraphDatabase
from dotenv import load_dotenv
from app.logging_utils import ai_logger, db_logger

load_dotenv()

class RAGState(TypedDict):
    query: str
    context: List[str]
    answer: str
    history: List[BaseMessage]
    folder_slug: str # Added for semantic isolation

class UndirectedRAGService:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        ai_logger.info("Undirected RAG Service initialized with Gemini & Neo4j Service.")

    def _get_undirected_context(self, query: str, folder_slug: str = None) -> List[str]:
        """
        Retrieves context by traversing edges in BOTH directions.
        Uses semantic folder label for FAST indexing and isolation if provided.
        """
        from app.services.neo4j_service import neo4j_service
        
        db_logger.info(f"Retrieving undirected context for: {query} (Folder: {folder_slug})")
        
        # If folder_slug provided, restrict to :Folder_<SLUG> for extreme speed
        folder_label_clause = f":Folder_{folder_slug}" if folder_slug else ""
        
        cypher = f"""
        MATCH (n{folder_label_clause})
        WHERE n.id CONTAINS $keyword OR n.id =~ $regex
        MATCH (n)-[r]-(m)
        RETURN n.id + ' ' + type(r) + ' ' + m.id as relationship
        LIMIT 50
        """
        keyword = query.split()[-1]
        regex = f"(?i).*{keyword}.*"
        
        context = []
        result = neo4j_service.run_query(cypher, {"keyword": keyword, "regex": regex})
        for record in result:
            context.append(record["relationship"])
        return context

    async def chat_node(self, state: RAGState):
        context = self._get_undirected_context(state['query'], state.get('folder_slug'))
        context_str = "\n".join(context)
        
        prompt = f"""
        You are the Neural Nexus V2 AI. You have access to a bi-directional Knowledge Graph.
        
        CONTEXT FROM GRAPH (BI-DIRECTIONAL):
        {context_str}
        
        QUESTION:
        {state['query']}
        
        INSTRUCTIONS:
        1. Use the bi-directional context to answer accurately. 
        2. If you see Herb-TREATS-Disease, and the user asks "What treats Disease?", you must identify the Herb.
        3. Be scientific and precise.
        """
        
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return {"answer": response.content, "context": context}

    def build_graph(self):
        workflow = StateGraph(RAGState)
        workflow.add_node("chat", self.chat_node)
        workflow.set_entry_point("chat")
        workflow.add_edge("chat", END)
        return workflow.compile()

rag_service = UndirectedRAGService()
rag_app = rag_service.build_graph()
