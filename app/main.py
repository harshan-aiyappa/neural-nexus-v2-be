from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Neural Nexus V2 API",
    description="Global Standard Backend using Gemini and Neo4j Native Labels",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Neural Nexus V2 Backend is running. Powered by Gemini & Neo4j."}

@app.get("/health")
async def health_check():
    # Placeholder for actual Neo4j and Gemini health checks
    return {"status": "healthy"}
