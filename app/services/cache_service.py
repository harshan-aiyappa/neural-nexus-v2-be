import redis
import os
import json
import logging
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info(f"[OK] connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"[WARN] Redis connection failed: {e}. Caching disabled.")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, expire: int = 3600):
        if not self.client:
            return
        try:
            self.client.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def delete(self, key: str):
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

cache_service = CacheService()
