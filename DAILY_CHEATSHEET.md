# 🗓️ Neural Nexus V2 — Daily Git Cheat Sheet

## 👤 Who Does What?

| Person                    | Branch                         | Files They Own                                                         |
| :------------------------ | :----------------------------- | :--------------------------------------------------------------------- |
| **Harshan**         | `feat/harshan/core-graph`    | `graph.py`, `neo4j_service.py`, `security.py`, `Discovery.tsx` |
| **Namitha**         | `feat/namitha/nexus-ai-chat` | `chat.py`, `gemini_service.py`, `Chat.tsx`                       |
| **Both merge into** | `dev` → `main`            | After review                                                           |

---

## ☀️ Start of Day (Do This Every Morning)

```bash
# 1. Sync dev with latest
git checkout dev
git pull origin dev

# 2. Merge dev into your branch to get latest changes
git checkout feat/harshan/core-graph      # (Harshan) or feat/namitha/nexus-ai-chat
git merge dev

# 3. Start working!
```

---

## 💾 During the Day (Commit Often)

```bash
# Save your work with a clear message
git add app/routers/graph.py
git commit -m "feat(graph): add filter by date range to full graph endpoint"

# Push to YOUR branch (not dev!)
git push origin feat/harshan/core-graph
```

### Commit Message Examples

| Type         | Example                                                      |
| :----------- | :----------------------------------------------------------- |
| `feat`     | `feat(chat): add context memory across messages`           |
| `fix`      | `fix(graph): resolve empty node list for phytochemical KG` |
| `chore`    | `chore(deps): update requirements.txt`                     |
| `docs`     | `docs: update API endpoint examples`                       |
| `refactor` | `refactor(security): extract IP allowlist to .env`         |

---

## 🌙 End of Day (Push + Merge to Dev)

```bash
# 1. Push your branch
git push origin feat/harshan/core-graph

# 2. Merge into dev (do this together if both worked today)
git checkout dev
git merge feat/harshan/core-graph
git push origin dev
```

---

## 🆘 Oh No, Merge Conflict!

```bash
# Step 1: See what conflicted
git status   # Look for "both modified"

# Step 2: Open the file and resolve:
# <<<<<<< yours
# your code
# =======
# their code
# >>>>>>> theirs
# → Keep the right version, delete the markers

# Step 3: Finish the merge
git add <conflicted-file>
git commit -m "fix(merge): resolve conflict in graph.py"
```

> [!TIP]
> Most conflicts will be in `App.tsx` (routes) and `main.py` (router registration). Just add BOTH sets of changes — routes don't conflict, they stack.

---

## 📦 What Goes to `main`?

Only run this when a feature is fully tested and stable:

```bash
git checkout main
git merge dev
git push origin main
```

---

## 🔍 Quick Inspection Commands

```bash
git log --oneline -10        # See last 10 commits
git diff HEAD                # See all unsaved changes
git stash                    # Temporarily hide changes
git stash pop                # Bring them back
git branch -a                # See all branches
```

---

## 🛠️ Services Quick Reference

| Service  | URL                          | Start Command                                                |
| :------- | :--------------------------- | :----------------------------------------------------------- |
| Backend  | `http://10.10.20.122:8000` | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` |
| Frontend | `http://10.10.20.122:5173` | `npm run dev`                                              |
| Redis UI | `http://10.10.20.122:8081` | Docker (already running)                                     |
| Neo4j    | `http://10.10.20.122:7474` | Running on server                                            |
