from app.services.chat.router import router as chat_router

# This file just re-exports the new router to maintain backward compatibility with __init__.py
router = chat_router
