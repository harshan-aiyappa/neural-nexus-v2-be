from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "VIEWER"

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class FolderCreate(BaseModel):
    name: str
    description: str = ""

class ExtractionRequest(BaseModel):
    text: str

class IngestionRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    folder_id: str

class ChatRequest(BaseModel):
    message: str
    context_folder: Optional[str] = None # Folder name/slug for isolation
    history: List[Dict[str, str]] = []

class GraphSearchRequest(BaseModel):
    query: str
    node_type: Optional[str] = None

class DeepAnalyzeRequest(BaseModel):
    node_id: str
    folder_slug: Optional[str] = None
    node_name: Optional[str] = None
    node_label: Optional[str] = None
