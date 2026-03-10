from app.services.gemini_service import gemini_service
from app.db.neo4j_utils import db_guardian
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(
    title="Neural Nexus V2 API",
    description="Global Standard Backend using Gemini and Neo4j Native Labels",
    version="2.0.0"
)

# ... CORS middleware ...

class ExtractionRequest(BaseModel):
    text: str

class IngestionRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    folder_id: str

@app.get("/")
async def root():
    return {"message": "Neural Nexus V2 Backend is running. Powered by Gemini & Neo4j."}

@app.post("/extract")
async def extract_knowledge(request: ExtractionRequest):
    """Gemini-powered structured extraction."""
    return await gemini_service.extract_scientific_entities(request.text)

@app.post("/ingest")
async def ingest_knowledge(request: IngestionRequest):
    """Symmetry Guardian & Native Label Ingestion."""
    await db_guardian.merge_entities_with_guardian(
        request.nodes, 
        request.relationships, 
        request.folder_id
    )
    return {"status": "success", "message": f"Graph ingested with label :Folder_{request.folder_id}"}

from app.services.rag_service import rag_app

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []

@app.post("/chat")
async def chat_with_nexus(request: ChatRequest):
    """LangGraph + Gemini bi-directional RAG."""
    result = await rag_app.ainvoke({
        "query": request.message,
        "history": [],
        "context": [],
        "answer": ""
    })
    return {"reply": result["answer"], "discovery_context": result["context"]}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
