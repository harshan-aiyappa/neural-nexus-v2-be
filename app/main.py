from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import logging

from app.routers import auth, graph, ingest, chat, folders
from app.services import neo4j_service
from app.db.mongo_utils import mongo_service
from app.logging_utils import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — verify connectivity on startup."""
    try:
        # Verify Neo4j
        neo4j_service.verify_connectivity()
        logger.info("[OK] Neo4j connection verified")
        
        # Verify Mongo (Async) - short timeout to not hang startup
        try:
            from pymongo.errors import ServerSelectionTimeoutError
            # We don't want to wait 30s for a failure
            await mongo_service.client.admin.command('ping', serverSelectionTimeoutMS=2000)
            logger.info("[OK] MongoDB connection verified")
        except Exception as mongo_err:
            logger.warning(f"[WARN] MongoDB unreachable (Guest Mode active): {mongo_err}")

    except Exception as e:
        logger.error(f"[WARN] Database connection failed: {e}")
    yield
    # Shutdown
    neo4j_service.close()
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
 
