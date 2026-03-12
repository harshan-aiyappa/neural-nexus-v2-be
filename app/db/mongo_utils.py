import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from typing import List, Dict
from app.logging_utils import db_logger

load_dotenv()

class MongoDBService:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client.get_database("neural_nexus_v2")
        db_logger.info(f"MongoDB Service initialized on {self.uri}")

    async def save_document(self, content: str, metadata: dict):
        """Save raw document content and metadata before graph extraction."""
        collection = self.db.get_collection("documents")
        document = {
            "content": content,
            "metadata": metadata,
            "status": "raw"
        }
        result = await collection.insert_one(document)
        return str(result.inserted_id)

    async def get_all_folders(self) -> List[Dict]:
        """Retrieve all scientific topics/folders."""
        db_logger.info("Fetching all folders from MongoDB")
        try:
            collection = self.db.get_collection("folders")
            cursor = collection.find({})
            folders = await cursor.to_list(length=100)
            for folder in folders:
                folder["id"] = str(folder.pop("_id"))
            db_logger.info(f"Retrieved {len(folders)} folders")
            return folders
        except Exception as e:
            db_logger.error(f"Failed to fetch folders: {e}")
            return []

    async def create_folder(self, name: str, description: str = "") -> str:
        """Initialize a new knowledge folder."""
        collection = self.db.get_collection("folders")
        folder = {
            "name": name,
            "description": description,
            "file_count": 0,
            "node_count": 0,
            "created_at": "...", # Use datetime.now() normally
            "updated_at": "...",
            "permission": "owner"
        }
        result = await collection.insert_one(folder)
        return str(result.inserted_id)

    async def delete_folder(self, folder_id: str):
        """Wipe folder metadata."""
        from bson import ObjectId
        collection = self.db.get_collection("folders")
        await collection.delete_one({"_id": ObjectId(folder_id)})

    async def save_chat_history(self, user_id: str, message: str, response: str):
        """Persist discovery chat history."""
        collection = self.db.get_collection("chat_history")
        await collection.insert_one({
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": "..." # Replace with actual timestamp logic if needed
        })

    async def get_recent_activity(self) -> List[Dict]:
        """Synthesize recent activity from folders and documents."""
        activities = []
        try:
            # Latest Folders
            folder_collection = self.db.get_collection("folders")
            folders = await folder_collection.find({}).sort("_id", -1).limit(3).to_list(length=3)
            for f in folders:
                activities.append({
                    "type": "Ingestion",
                    "title": f"Folder: {f['name']}",
                    "result": f"{f.get('file_count', 0)} Files",
                    "date": "Recently",
                    "color": "turf-green-3"
                })
                
            # Latest Documents
            doc_collection = self.db.get_collection("documents")
            docs = await doc_collection.find({}).sort("_id", -1).limit(3).to_list(length=3)
            for d in docs:
                activities.append({
                    "type": "Extraction",
                    "title": d.get("metadata", {}).get("filename", "Untitled Document"),
                    "result": "Processed",
                    "date": "Recently",
                    "color": "jungle-teal"
                })
        except Exception as e:
            db_logger.error(f"Failed to fetch recent activity: {e}")
            
        return activities

mongo_service = MongoDBService()
