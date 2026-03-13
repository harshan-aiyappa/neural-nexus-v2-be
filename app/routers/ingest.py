import io
import pandas as pd
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from pydantic import BaseModel
from app.models.schemas import IngestionRequest, ExtractionRequest
from app.services.neo4j_service import neo4j_service
from app.services.excel_service import excel_service
from app.services.gemini_service import gemini_service
from app.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload-cypher")
async def upload_cypher(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a .cypher file and execute it in a specific folder context.
    Uses label-scoping to isolate the data.
    """
    if not file.filename.endswith('.cypher'):
        raise HTTPException(status_code=400, detail="Only .cypher files are supported")
    
    content = await file.read()
    cypher_text = content.decode('utf-8')
    
    # Process in background to prevent timeout
    background_tasks.add_task(
        neo4j_service.execute_cypher_scoped, 
        cypher_text, 
        folder_id
    )
    
    return {"status": "Processing", "filename": file.filename, "folder": folder_id}

@router.post("/extract")
async def extract_knowledge(request: ExtractionRequest, current_user: dict = Depends(get_current_user)):
    """Extract entities and relationships from raw text using LLM."""
    try:
        result = await gemini_service.extract_graph(request.text)
        return result
    except Exception as e:
        logger.error(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
async def ingest_knowledge(request: IngestionRequest, current_user: dict = Depends(get_current_user)):
    """Ingest nodes and relationships into a folder with Symmetry Guardian protection."""
    try:
        await neo4j_service.merge_entities_with_guardian(
            request.nodes, 
            request.relationships, 
            request.folder_id
        )
        return {"status": "Success", "nodes": len(request.nodes), "rels": len(request.relationships)}
    except Exception as e:
        logger.error(f"Ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel")
async def ingest_excel(
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Ingest structured data from Excel/CSV."""
    if not file.filename.endswith(('.xlsx', '.csv')):
        raise HTTPException(status_code=400, detail="Unsupported file format")
    
    content = await file.read()
    df = pd.read_excel(io.BytesIO(content)) if file.filename.endswith('.xlsx') else pd.read_csv(io.BytesIO(content))
    
    # Use Excel service for complex mapping
    result = await excel_service.process_and_ingest(df, folder_id)
    return {"status": "Success", "details": result}
