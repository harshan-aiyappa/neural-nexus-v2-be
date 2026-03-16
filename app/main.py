from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import logging

from app.routers import auth, graph, ingest, chat, folders, settings, analytics
from app.services import neo4j_service
from app.db.mongo_utils import mongo_service
from app.logging_utils import logger

import os
import redis
from google import genai

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — verify connectivity on startup."""
    services_status = []
    
    # 1. Verify Neo4j
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    try:
        await neo4j_service.verify_connectivity()
        await neo4j_service.setup_constraints()
        services_status.append(("Neo4j", neo4j_uri, "✅ OK"))
    except Exception as e:
        services_status.append(("Neo4j", neo4j_uri, f"❌ FAILED ({str(e)[:30]}...)"))

    # 2. Verify MongoDB
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    try:
        import asyncio
        await asyncio.wait_for(mongo_service.client.admin.command('ping'), timeout=2.0)
        services_status.append(("MongoDB", mongo_uri, "✅ OK"))
    except Exception as e:
        services_status.append(("MongoDB", mongo_uri, f"❌ FAILED ({str(e)[:30]}...)"))

    # 3. Verify Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url, socket_timeout=2)
        r.ping()
        services_status.append(("Redis", redis_url, "✅ OK"))
    except Exception as e:
        services_status.append(("Redis", redis_url, f"❌ FAILED ({str(e)[:30]}...)"))

    # 4. Verify Gemini API
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        if not api_key:
            raise ValueError("No API Key found in .env")
        
        # New SDK verification
        client = genai.Client(api_key=api_key)
        # Verify with a lightweight call (checking models)
        client.models.get(model=model_name)
        services_status.append(("Gemini API", "Cloud", "✅ OK"))
    except Exception as e:
        err_msg = str(e).lower()
        status = "❌ FAILED (Expired/Invalid)" if "expired" in err_msg or "400" in err_msg else f"❌ FAILED ({str(e)[:20]})"
        services_status.append(("Gemini API", "Cloud", status))

    # 5. Trigger Background Embedding Backfill (Step ID: 226)
    if all(s[2] == "✅ OK" for s in services_status if s[0] in ["Neo4j", "Gemini API"]):
        import asyncio
        asyncio.create_task(neo4j_service.process_embeddings_batch())
        logger.info("[INIT] Neo4j Embedding Backfill started in background")

    # Log Service Dashboard
    dashboard = ["\n" + "="*60, "       NEURAL NEXUS V2 - SERVICE CONNECTIVITY DASHBOARD", "="*60, f"{'SERVICE':<15} | {'URI/LOCATION':<30} | {'STATUS'}", "-" * 60]
    for name, uri, status in services_status:
        short_uri = (uri[:27] + "...") if len(uri) > 30 else uri
        dashboard.append(f"{name:<15} | {short_uri:<30} | {status}")
    dashboard.append("="*60 + "\n")
    
    for line in dashboard:
        logger.info(line)

    yield
    # Shutdown
    await neo4j_service.close()
    logger.info("[OK] Database connections closed")

app = FastAPI(
    title="Neural Nexus V2 - Scientific Knowledge Graph",
    description="Research platform with Modular RBAC and Graph RAG",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root/Health
@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "Neural Nexus V2 API running", 
        "version": "2.0.0",
        "master_standard": "Native Labels & Symmetry Guardian active"
    }

# Register Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(folders.router, prefix="/api/folders", tags=["Folders"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Ingest"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
