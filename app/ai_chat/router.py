from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import ChatRequest
from app.core.security import get_current_user
from app.ai_chat.rag_service import chat_rag_service

router = APIRouter()

@router.post("", dependencies=[Depends(get_current_user)])
async def ask_question(request: ChatRequest):
    """
    Ask a research question — answered via isolated Graph RAG Pipeline.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        response = await chat_rag_service.answer(request.message, request.context_folder)
        return {
            "reply": response.get("answer"),
            "context": [response.get("context", "")],
            "cypher_used": response.get("cypher_used", ""),
            "gds_context": response.get("gds_context", ""),
            "search_mode": response.get("search_mode", ""),
            "vector_results": response.get("vector_results", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")
