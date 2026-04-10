# Neural Nexus V2 - Team Collaboration Guide

## Team Roles

| Developer   | Focus Area                                   |
| :---------- | :------------------------------------------- |
| **Harshan** | Core Backend, Graph Engine, Security, DevOps |
| **Namitha** | AI Chat (Nexus AI), LLM Integration, Chat UI |

---

## Git Branching Strategy

Always use `dev` as your integration base. Create feature branches for all new work.

```
main (production)
  └── dev (integration — merge here after review)
        ├── feat/harshan/* (core, graph, infra)
        └── feat/namitha/nexus-ai-chat (AI chat)
```

### Daily Workflow

```bash
# 1. Start of day — sync with dev
git checkout dev && git pull origin dev

# 2. Switch to your feature branch, pull latest dev into it
git checkout feat/namitha/nexus-ai-chat
git merge dev

# 3. Work → commit often with clear messages
git commit -m "feat(chat): improve multi-hop context window"

# 4. Push and open a PR into dev
git push origin feat/namitha/nexus-ai-chat
```

---

## File Ownership (Minimize Conflicts)

> [!TIP]
> These areas are naturally separate. If you stay in your zone, Git will handle merges automatically ~90% of the time.

### Harshan's Zone
- `app/routers/graph.py`, `app/services/neo4j_service.py`
- `app/core/security.py`, `app/db/`
- `src/pages/Discovery.tsx`, `src/pages/Library.tsx`, `src/pages/Dashboard.tsx`

### Namitha's Zone
- `app/routers/chat.py`, `app/services/gemini_service.py`
- `src/pages/Chat.tsx`, `src/components/chat/`

### Shared (coordinate before editing)
- `app/main.py` (router registration)
- `src/App.tsx` (route registration)
- `src/services/api.ts` (API client)
- `requirements.txt`, `package.json`

---

## Environment Setup

Share the same `.env` values. Do NOT commit `.env` to git.

```env
MONGODB_URI=mongodb://10.10.20.144:27017
NEO4J_URI=bolt://10.10.20.144:7687
REDIS_URL=redis://10.10.20.144:6379/0
GEMINI_API_KEY=<your key>
```

---

## Services & Ports

| Service       | Address                        | Notes           |
| :------------ | :----------------------------- | :-------------- |
| Backend API   | `http://10.10.20.144:8000`     | FastAPI         |
| Frontend      | `http://10.10.20.144:5173`     | Vite dev server |
| Redis UI      | `http://10.10.20.144:8081`     | Redis Commander |
| Neo4j Browser | `http://10.10.20.144:7474`     |                 |
| MongoDB       | `mongodb://10.10.20.144:27017` |                 |
