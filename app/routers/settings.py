from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
from app.core.security import RoleChecker

router = APIRouter()
admin_only = Depends(RoleChecker(["ADMIN"]))

class KeyUpdateRequest(BaseModel):
    key_name: str
    key_value: str

@router.post("/update-key", dependencies=[admin_only])
async def update_api_key(request: KeyUpdateRequest):
    """
    Dynamically update environmental keys.
    Note: For production, this should update a secret manager or a persistent store.
    For this V2 prototype, we will update the .env if writable, and the current os.environ.
    """
    if request.key_name not in ["GEMINI_API_KEY", "NEO4J_PASSWORD", "MONGODB_URI"]:
        raise HTTPException(status_code=400, detail="Restricted key update")
    
    try:
        # Update current process environment
        os.environ[request.key_name] = request.key_value
        
        # Attempt to persist to .env for next restart
        env_path = ".env"
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            
            with open(env_path, "w") as f:
                for line in lines:
                    if line.startswith(f"{request.key_name}="):
                        f.write(f"{request.key_name}={request.key_value}\n")
                    else:
                        f.write(line)
        
        return {"success": True, "message": f"{request.key_name} updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update key: {str(e)}")

@router.get("/status")
async def get_system_status():
    """Get status of external dependencies."""
    return {
        "gemini": "ACTIVE" if os.getenv("GEMINI_API_KEY") else "MISSING",
        "neo4j": "CONNECTED", # Placeholder for real check
        "mongodb": "CONNECTED"
    }
