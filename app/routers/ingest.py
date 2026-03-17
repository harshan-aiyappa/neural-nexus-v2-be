import io
import pandas as pd
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from pydantic import BaseModel
from app.models.schemas import IngestionRequest, ExtractionRequest
from app.services.neo4j_service import neo4j_service
from app.services.excel_service import excel_service
from app.services.gemini_service import gemini_service
from app.services.ingest_service import ingest_service
from app.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload-cypher", summary="Bulk Protocol Commit", description="Upload and execute a large Cypher transaction directly into the Knowledge Graph.")
async def upload_cypher(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a .cypher file and execute it in a specific folder context.
    Uses label-scoping and Symmetry Guardian protection.
    """
    if not file.filename.endswith('.cypher'):
        raise HTTPException(status_code=400, detail="Only .cypher files are supported")
    
    content = await file.read()
    cypher_text = content.decode('utf-8')
    
    # Process with IngestService (which includes Guardian sync)
    background_tasks.add_task(
        ingest_service.ingest_cypher_bulk, 
        cypher_text, 
        folder_id,
        user_email=current_user.get("email", "System")
    )
    
    return {"status": "Processing", "filename": file.filename, "folder": folder_id}

@router.post("/extract", summary="LLM Knowledge Distillation", description="Directly extract entities and relationships from raw text using the Gemini reasoning engine.")
async def extract_knowledge(request: ExtractionRequest, current_user: dict = Depends(get_current_user)):
    """
    Hybrid Extraction:
    - Uses Celery if Redis Broker is available.
    - Falls back to Sync extraction if Broker is down (Resilience Pillar).
    """
    from app.services.gemini_service import gemini_service, extract_knowledge_task
    from app.services.cache_service import cache_service
    
    # Check if we should use Async flow (Requires Redis)
    use_async = cache_service.client is not None
    
    if use_async:
        try:
            task = extract_knowledge_task.delay(request.text)
            logger.info(f"Offloaded extraction to Celery: {task.id}")
            return {"status": "Processing", "task_id": task.id, "mode": "async"}
        except Exception as e:
            logger.warning(f"Celery dispatch failed: {e}. Falling back to Sync mode.")
            # Fall through to sync

    # Sync Fallback (Legacy/Resilient mode)
    try:
        logger.info("Running Synchronous Extraction (Redis/Celery offline)")
        result = await gemini_service.extract_scientific_entities(request.text)
        return {"status": "Success", "result": result, "mode": "sync"}
    except Exception as e:
        logger.error(f"extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}")
async def get_task_status(task_id: str, current_user: dict = Depends(get_current_user)):
    """Check the status of an asynchronous extraction task."""
    try:
        from app.core.celery_app import celery_app
        from celery.result import AsyncResult
        
        res = AsyncResult(task_id, app=celery_app)
        if res.state == 'PENDING':
            return {"status": "Pending", "progress": 0}
        elif res.state == 'SUCCESS':
            return {"status": "Success", "result": res.result}
        elif res.state == 'FAILURE':
            return {"status": "Failure", "error": str(res.info)}
        return {"status": res.state}
    except (ImportError, Exception) as e:
        logger.error(f"Task status retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Task tracking unavailable (Redis offline)")

@router.post("/ingest", summary="Structured Knowledge Committal", description="Inject pre-processed nodes and relationships into the graph with Symmetry Guardian validation.")
async def ingest_knowledge(request: IngestionRequest, current_user: dict = Depends(get_current_user)):
    """Ingest nodes and relationships into a folder with Symmetry Guardian protection."""
    try:
        result = await ingest_service.ingest_nodes_rels(
            request.nodes, 
            request.relationships, 
            request.folder_id,
            user_email=current_user.get("email", "System")
        )
        return result
    except Exception as e:
        logger.error(f"Ingestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/excel", summary="Tabular Data Ingestion", description="Transform and upload CSV/XLSX data into the graph schema automatically.")
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
@router.post("/universal", summary="Multimodal Intelligence Upload", description="Unified entry point for PDF, CSV, Excel, and Text files with automated AI reasoning.")
async def universal_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str = Form(...),
    use_ai: bool = Form(True),
    current_user: dict = Depends(get_current_user)
):
    """
    Universal Upload Endpoint:
    - Accepts PDF, CSV, XLSX, TXT, CYPHER.
    - Triggers Gemini-powered extraction and vector storage.
    """
    allowed_ext = ('.pdf', '.csv', '.xlsx', '.txt', '.cypher')
    if not file.filename.lower().endswith(allowed_ext):
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Allowed: {allowed_ext}")
    
    content = await file.read()
    
    # Process with IngestService
    background_tasks.add_task(
        ingest_service.ingest_from_any_source, 
        content, 
        file.filename, 
        folder_id,
        user_email=current_user.get("email", "System"),
        use_ai=use_ai
    )
    
    return {
        "status": "Processing", 
        "filename": file.filename, 
        "folder": folder_id,
        "mode": "ai_enhanced" if use_ai else "direct"
    }
