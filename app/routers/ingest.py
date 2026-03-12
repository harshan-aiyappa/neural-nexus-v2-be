from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from app.models.schemas import IngestionRequest
from app.services.neo4j_service import neo4j_service
from app.services.excel_service import excel_service
from app.core.security import get_current_user, RoleChecker

router = APIRouter()

# Only Researchers and Admins can ingest data
researcher_only = Depends(RoleChecker(["ADMIN", "RESEARCHER"]))

def clean_cypher(cypher_text: str) -> str:
    """Removes comments and empty lines from Cypher scripts to prevent parser errors."""
    lines = cypher_text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//") or not stripped:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

@router.post("/excel/{folder_id}")
async def ingest_excel(folder_id: str, file: UploadFile = File(...), _=researcher_only):
    """Scientific Excel ingestion with Symmetry Guardian."""
    try:
        content = await file.read()
        import io
        import pandas as pd
        df = pd.read_excel(io.BytesIO(content))
        result = await excel_service.process_and_ingest(df, folder_id)
        return {"success": True, "details": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cypher", dependencies=[researcher_only])
async def run_cypher(request: dict, background_tasks: BackgroundTasks):
    """Execute raw Cypher query (Zip feature)."""
    try:
        cypher = request.get("cypher")
        folder_id = request.get("folder_id")
        if not cypher or not folder_id:
            raise HTTPException(status_code=400, detail="Cypher query and folder_id are required")
        cleaned_cypher = clean_cypher(cypher)
        result = neo4j_service.execute_cypher(cleaned_cypher)
        
        # Tag newly created or modified nodes with the folder
        neo4j_service.run_query(f"MATCH (n) WHERE NOT n:Folder_{folder_id} SET n:Folder_{folder_id}")
        
        # Trigger background embedding task specifically for this folder
        background_tasks.add_task(neo4j_service.process_embeddings_batch, folder_id)
        
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Form
@router.post("/upload-cypher", dependencies=[researcher_only])
async def upload_cypher(background_tasks: BackgroundTasks, file: UploadFile = File(...), folder_id: str = Form(...)):
    """Upload .cypher file (Zip feature)."""
    if not file.filename.endswith((".cypher", ".txt")):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    content = await file.read()
    cypher = content.decode("utf-8")
    try:
        cleaned_cypher = clean_cypher(cypher)
        result = neo4j_service.execute_cypher(cleaned_cypher)
        
        # Tag newly created or modified nodes with the folder
        neo4j_service.run_query(f"MATCH (n) WHERE NOT n:Folder_{folder_id} SET n:Folder_{folder_id}")
        
        # Trigger background embedding task
        background_tasks.add_task(neo4j_service.process_embeddings_batch, folder_id)
        
        return {"success": True, "filename": file.filename, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
