from typing import Dict, Any, List, Optional
from app.services.neo4j_service import neo4j_service
from app.services.gemini_service import gemini_service
from app.logging_utils import ai_logger

class AnalyticChatService:
    async def analyze(self, query: str, folder_slug: str) -> Dict[str, Any]:
        """
        Specialized analytical reasoning for graph data.
        Handles: "What are the top-K nodes?", "Show me the path between X and Y", etc.
        """
        ai_logger.info(f"Executing Analytic Graph Query: {query}")
        
        # Step 1: LLM-driven Intent to Cypher Translation
        # This is strictly restricted to biological/chemical entities and folder isolation.
        system_prompt = f"""
        You are a Graph Data Science (GDS) Analyst for Neural Nexus.
        Translate the user's analytical question into a precise Cypher query.
        
        Constraints:
        1. Only use nodes tagged with label `:Folder_{folder_slug}`.
        2. Focus on: Centrality, Community, Paths, and Distributions.
        3. Return ONLY the Cypher query.
        
        Examples:
        - "What are the most connected chemicals?" -> "MATCH (n:Chemical:Folder_{folder_slug}) RETURN n.name, count((n)--()) as connections ORDER BY connections DESC LIMIT 5"
        """
        
        cypher = await gemini_service.generate_response(query, system_prompt)
        cypher = cypher.strip("`").replace("cypher\n", "").strip()
        
        ai_logger.info(f"Generated Analytic Cypher: {cypher}")
        
        try:
            results = await neo4j_service.run_query(cypher)
            
            # Step 2: Insight Synthesis
            synthesis_prompt = f"Synthesize these graph results into a brief, professional research insight for the user. Results: {results}"
            insight = await gemini_service.generate_response(query, synthesis_prompt)
            
            return {
                "answer": insight,
                "cypher": cypher,
                "data": results
            }
        except Exception as e:
            ai_logger.error(f"Analytic Chat Error: {e}")
            return {"answer": f"I encountered an error calculating that metric: {str(e)}", "cypher": cypher, "data": []}

analytic_chat_service = AnalyticChatService()
