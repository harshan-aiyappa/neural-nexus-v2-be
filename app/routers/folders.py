from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import FolderCreate
from app.db.mongo_utils import mongo_service
from app.core.security import get_current_user, RoleChecker

router = APIRouter()

# Allow all researchers to manage folders
researcher_only = Depends(RoleChecker(["ADMIN", "RESEARCHER"]))

@router.get("/", dependencies=[Depends(get_current_user)])
async def get_folders():
    from app.services.neo4j_service import neo4j_service
    folders = await mongo_service.get_all_folders()
    counts = neo4j_service.get_folder_node_counts()
    
    for folder in folders:
        # Use semantic slug to match node counts
        slug = neo4j_service.slugify_folder(folder["name"])
        folder["slug"] = slug
        folder["node_count"] = counts.get(slug, 0)
        
    return folders

@router.post("/", dependencies=[researcher_only])
async def create_folder(folder: FolderCreate):
    folder_id = await mongo_service.create_folder(folder.name, folder.description)
    return {"id": folder_id, "name": folder.name}

@router.delete("/{folder_id}", dependencies=[researcher_only])
async def delete_folder(folder_id: str):
    await mongo_service.delete_folder(folder_id)
    return {"status": "success"}
