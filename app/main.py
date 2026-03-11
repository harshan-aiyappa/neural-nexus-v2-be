from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.gemini_service import gemini_service
from app.services.excel_service import excel_service
from app.db.neo4j_utils import db_guardian
from pydantic import BaseModel
from typing import List, Dict, Any
from app.logging_utils import logger, db_logger
import time

app = FastAPI(
    title="Neural Nexus V2 API",
    description="Global Standard Backend using Gemini and Neo4j Native Labels",
    version="2.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Neural Nexus V2 Services...")
    logger.info("Global Master Standards: Native Labels & Symmetry Guardian active.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractionRequest(BaseModel):
    text: str

class IngestionRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    folder_id: str

from app.db.mongo_utils import mongo_service

class FolderCreate(BaseModel):
    name: str
    description: str = ""

@app.get("/folders")
async def get_folders():
    return await mongo_service.get_folders()

@app.post("/folders")
async def create_folder(folder: FolderCreate):
    folder_id = await mongo_service.create_folder(folder.name, folder.description)
    return {"id": folder_id, "status": "created"}

@app.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    await mongo_service.delete_folder(folder_id)
    return {"status": "deleted"}

@app.get("/health/mongo")
async def mongo_health():
    try:
        await mongo_service.client.admin.command('ping')
        return {"status": "connected", "database": "neural_nexus_v2"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/extract")
async def extract_knowledge(request: ExtractionRequest):
    """Gemini-powered structured extraction."""
    logger.info(f"Incoming extraction request. Text length: {len(request.text)}")
    start_time = time.time()
    result = await gemini_service.extract_scientific_entities(request.text)
    duration = time.time() - start_time
    logger.info(f"Extraction completed in {duration:.2f}s. Found {len(result.get('nodes', []))} nodes.")
    return result

@app.post("/ingest")
async def ingest_knowledge(request: IngestionRequest):
    """Symmetry Guardian & Native Label Ingestion."""
    await db_guardian.merge_entities_with_guardian(
        request.nodes, 
        request.relationships, 
        request.folder_id
    )
    return {"status": "success", "message": f"Graph ingested with label :Folder_{request.folder_id}"}

class ExcelIngestRequest(BaseModel):
    file_path: str
    folder_id: str

@app.post("/ingest/excel")
async def ingest_excel(request: ExcelIngestRequest):
    """XLSX -> Gemini -> Neo4j Guardian Ingestion."""
    logger.info(f"Incoming Excel ingestion request for {request.file_path}")
    result = await excel_service.process_excel(request.file_path, request.folder_id)
    return result

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
