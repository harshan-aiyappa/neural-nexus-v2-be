from fastapi import APIRouter, HTTPException, Depends
import os
import redis
import asyncio
from pydantic import BaseModel
from google import genai
from app.core.security import RoleChecker
from app.services.neo4j_service import neo4j_service
from app.db.mongo_utils import mongo_service

router = APIRouter()
admin_only = Depends(RoleChecker(["ADMIN"]))

class KeyUpdateRequest(BaseModel):
    key_name: str
    key_value: str

@router.post("/update-key", dependencies=[admin_only], summary="Secret Key Rotation", description="Updates sensitive environmental variables (Gemini API Key, Neo4j Password) with automatic .env persistence.")
async def update_api_key(request: KeyUpdateRequest):
    """
    Dynamically update environmental keys.
    Note: For production, this should update a secret manager or a persistent store.
    For this prototype, we will update the .env if writable, and the current os.environ.
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

from google import genai
from app.services import neo4j_service
from app.db.mongo_utils import mongo_service
import asyncio

class KeyVerifyRequest(BaseModel):
    key_value: str

@router.post("/verify-key", dependencies=[admin_only], summary="Key Health Check", description="Performs a dry-run API call using the provided key string to verify its operational status before persistence.")
async def verify_api_key(request: KeyVerifyRequest):
    """Attempt to use the provided key with a lightweight model call."""
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        client = genai.Client(api_key=request.key_value)
        # Verify with a lightweight call
        client.models.get(model=model_name)
        return {"success": True, "message": "Key validated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Key validation failed: {str(e)}")

@router.get("/status", summary="Infrastructure Pulse", description="Returns real-time connectivity states for Gemini, Neo4j, MongoDB, and Redis clusters.")
async def get_system_status():
    """Get real-time connectivity status of all external services."""
    status = {
        "gemini": "OFFLINE",
        "neo4j": "OFFLINE",
        "mongodb": "OFFLINE",
        "redis": "OFFLINE",
        "celery": "OFFLINE"
    }

    # 1. Neo4j Check
    try:
        await neo4j_service.verify_connectivity()
        status["neo4j"] = "ACTIVE"
    except:
        pass

    # 2. MongoDB Check
    try:
        await asyncio.wait_for(mongo_service.client.admin.command('ping'), timeout=1.0)
        status["mongodb"] = "ACTIVE"
    except:
        pass

    # 3. Redis Check
    try:
        redis_url = os.getenv("REDIS_URL", "redis://10.10.20.122:6379/0")
        client = redis.from_url(redis_url, socket_timeout=1)
        client.ping()
        status["redis"] = "ACTIVE"
    except:
        pass

    # 4. Gemini Check (using current env)
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        if api_key:
            client = genai.Client(api_key=api_key)
            client.models.get(model=model_name)
            status["gemini"] = "ACTIVE"
    except:
        pass

    # 5. Celery Check
    try:
        from app.core.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=0.5)
        pings = inspect.ping()
        status["celery"] = "ACTIVE" if pings else "IDLE"
    except:
        status["celery"] = "ERROR"

    return status
