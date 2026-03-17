from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import ChatRequest
from app.core.security import get_current_user
from app.services.chat.enhanced_rag import enhanced_rag_service
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

@router.post("", dependencies=[Depends(get_current_user)])
async def ask_question(request: ChatRequest):
    """
    Ask a research question — answered via the new Enhanced RAG Pipeline.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Convert dictionary history to LangChain messages
    history = []
    for msg in request.history:
        if msg.get("role") == "user":
            history.append(HumanMessage(content=msg.get("content", "")))
        else:
            history.append(AIMessage(content=msg.get("content", "")))

    try:
        response = await enhanced_rag_service.chat(
            user_query=request.message,
            folder_slug=request.context_folder,
            history=history
        )
        
        # Map to legacy keys for frontend compatibility
        return {
            "reply": response.get("answer"),
            "answer": response.get("answer"), # Keep both for safety
            "context": response.get("context", []),
            "grounding_score": response.get("grounding_score", 0.0),
            "search_mode": "hybrid_advanced"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Enhanced RAG pipeline error: {str(e)}")
