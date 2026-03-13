from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import ChatRequest
from app.core.security import get_current_user
from app.logging_utils import ai_logger
from app.services.chat.enhanced_rag import enhanced_rag_service
from app.services.chat.analytic_chat import analytic_chat_service

router = APIRouter()

@router.post("/", dependencies=[Depends(get_current_user)])
async def chat_with_nexus(request: ChatRequest):
    """
    Intention Router for Chat Services.
    Routes queries to either the RAG engine or the Analytics engine based on intent.
    """
    ai_logger.info(f"Incoming chat request: {request.message} (Folder: {request.context_folder})")
    
    # Simple heuristic routing for now. 
    # If the user asks for "most", "top", "rank", "important", "connected", "cluster", route to analytics.
    analytics_keywords = ["most", "top", "rank", "important", "connected", "cluster", "trace", "path"]
    query_lower = request.message.lower()
    
    is_analytics = any(keyword in query_lower for keyword in analytics_keywords)
    
    try:
        if is_analytics:
            response = await analytic_chat_service.analyze(request.message, request.context_folder)
        else:
            ai_logger.info("Routing to Enhanced RAG Engine")
            response = await enhanced_rag_service.chat(
                user_query=request.message,
                folder_slug=request.context_folder
            )
            
        return {
            "reply": response.get("answer"), 
            "context": response.get("context", []),
            "grounding_score": response.get("grounding_score", 0.0),
            "engine": "Analytics" if is_analytics else "RAG"
        }
    except Exception as e:
        ai_logger.error(f"Chat router error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
