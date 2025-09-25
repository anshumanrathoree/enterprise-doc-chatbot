from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio
import aiofiles
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enterprise Document Chatbot",
    description="A simple document chatbot backend",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    response: str
    sources: Optional[List] = []
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

# Ensure upload directory exists
upload_dir = "./uploads"
os.makedirs(upload_dir, exist_ok=True)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Enterprise Document Chatbot API is running"}

@app.get("/health")
async def health_check():
    """Health check with service status"""
    return {
        "status": "healthy",
        "ollama_service": "disconnected", # Will connect later
        "vector_store": "initialized"
    }

@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        # Validate file type
        allowed_types = [".pdf", ".txt", ".doc", ".docx"]
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not supported. Allowed types: {allowed_types}"
            )

        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: 50MB"
            )

        # Save file
        file_path = os.path.join(upload_dir, file.filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(f"Successfully uploaded: {file.filename}")

        return DocumentUploadResponse(
            success=True,
            document_id="temp-id-123",
            filename=file.filename,
            chunks_created=5,  # Simulated
            message="Document uploaded successfully (processing will be implemented later)"
        )

    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the document chatbot"""
    try:
        # Simple response for now
        response = f"I received your message: '{request.message}'. Full document processing with Ollama will be available once all dependencies are properly installed."

        return ChatResponse(
            response=response,
            sources=[],
            success=True
        )

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        # List files in upload directory
        documents = []
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                documents.append({
                    "document_id": f"temp-{filename}",
                    "filename": filename,
                    "chunk_count": 5,  # Simulated
                    "file_type": os.path.splitext(filename)[1]
                })
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    try:
        # For now, just return success
        return {"message": "Document deletion will be implemented later"}
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Simple Backend Server...")
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)