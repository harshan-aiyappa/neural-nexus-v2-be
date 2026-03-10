# Neural Nexus V2 - Backend

This is the V2 backend for the Neural Nexus project. It is built as a complete architectural rewrite based on the "Global Master Standards" identified during the analysis phase.

## Core Advancements in V2 (Compared to V1)
1.  **AI Engine Swap**: Completely powered by Google Gemini API (replacing Ollama).
2.  **Native Folder Labels**: Shifted from `folder_id` properties to dynamic Neo4j labels (`:Folder_XYZ`) for O(1) query speeds.
3.  **Symmetry Guardian**: Backend safeguards ensure mathematically pure relationships for Graph Data Science (GDS).
4.  **Undirected RAG**: Eliminates retrieval blind spots for accurate contextual reasoning.

## Getting Started

1.  **Environment Setup**:
    Copy `.env.example` to `.env` and fill in your Gemini API Key and Neo4j credentials.
    ```bash
    cp .env.example .env
    ```

2.  **Install Requirements**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Server**:
    ```bash
    uvicorn app.main:app --reload
    ```
