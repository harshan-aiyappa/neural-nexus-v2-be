# Neural Nexus - System Startup Guide

This document outlines the operational status and startup procedures for all services in the Neural Nexus platform.

## Infrastructure Services

| Service | Port | Status | Managed By |
| :--- | :--- | :--- | :--- |
| **Neo4j** | 7687 | ✅ UP | Homebrew (`brew services`) |
| **MongoDB** | 27017 | ✅ UP | Homebrew (`brew services`) |
| **Valkey (Cache/Queue)** | 6379 | ✅ UP | Docker |
| **Ollama (Local LLM)** | 11434 | ✅ UP | Homebrew / `ollama run` |

## Application Services

### 1. Backend API (FastAPI)
- **Status**: ✅ Running on `http://10.10.20.144:8000`
- **Command**: `source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Docs**: `http://10.10.20.144:8000/docs`

### 2. Background Worker (Celery)
- **Status**: ✅ Active
- **Command**: `source .venv/bin/activate && celery -A app.core.celery_app worker --loglevel=info`

### 3. Frontend (Vite/React)
- **Status**: ✅ Running on `http://10.10.20.144:5173`
- **Command**: `npm run dev` in `neural-nexus-v2-fe` directory.

---

## Quick Start & Stop Commands
Copy and paste these snippets directly into your terminal.

**1. Start Databases (Neo4j, MongoDB, Valkey) via Homebrew:**
```bash
/opt/homebrew/bin/brew services start neo4j mongodb-community@7.0 redis
```

**2. Stop Databases via Homebrew:**
```bash
/opt/homebrew/bin/brew services stop neo4j mongodb-community@7.0 redis
```

**3. Start Backend API (in `neural-nexus-v2-be`):**
```bash
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**4. Start Background Worker (in `neural-nexus-v2-be`):**
```bash
source .venv/bin/activate && celery -A app.core.celery_app worker --loglevel=info
```

**5. Start Frontend (in `neural-nexus-v2-fe`):**
```bash
npm run dev
```

---

## Access Points & UI Navigation
Once the services are running, here is what you will see on each port:

### 🌐 Frontend Web Application
- **URL**: [http://10.10.20.144:5173](http://10.10.20.144:5173)
- **What you'll see**: The main Neural Nexus dashboard. This is the interactive UI where you can perform graph searches, RAG chats, and ecosystem highlights.

### ⚙️ Backend API & Documentation
- **URL**: [http://10.10.20.144:8000/docs](http://10.10.20.144:8000/docs)
- **What you'll see**: The interactive FastAPI Swagger UI. Here you can manually test backend endpoints (like `/api/chat` or `/api/ingest`) without needing the frontend.

### 🧠 Graph Database Console
- **URL**: [http://10.10.20.144:7474](http://10.10.20.144:7474) (Default Neo4j HTTP port)
- **What you'll see**: The Neo4j Browser interface. Use this to view visual representations of your graph data and run manual Cypher queries. *(Note: Bolt connection for code uses port `7687`)*.

### 🤖 Local AI Engine (Ollama)
- **URL**: [http://10.10.20.144:11434](http://10.10.20.144:11434)
- **What you'll see**: A simple text confirmation that "Ollama is running". It functions as a background REST API for `llama3` and `nomic-embed-text` interactions.

---

## Key Environment Updates
- **Neo4j Password:** Confirmed as `harsh221996` in `.env`.
- **IP Addressing:** All configurations dynamically set to host IP `10.10.20.144` instead of `localhost`.
- **LLM Connectivity:** Now routing exclusively to local `Ollama` (`llama3:latest`, `nomic-embed-text:latest`) rather than cloud-based Gemini.

## Documentation Organization
All architectural and legacy markdown files have been moved to:
- `neural-nexus-v2-be/docs/md_files/`
- `neural-nexus-v2-fe/docs/md_files/`
