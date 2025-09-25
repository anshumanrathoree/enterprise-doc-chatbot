from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []

class DocumentChunk(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}
    similarity_score: Optional[float] = None

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[DocumentChunk]] = []
    success: bool = True

class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str
    filename: str
    chunks_created: int
    message: str

class HealthResponse(BaseModel):
    status: str
    ollama_service: str
    vector_store: str
    error: Optional[str] = None