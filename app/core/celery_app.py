import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "neural_nexus",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.services.gemini_service", "app.services.ingest_service"] # Register tasks here
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300, # 5 minutes max per extraction
)

if __name__ == "__main__":
    celery_app.start()
