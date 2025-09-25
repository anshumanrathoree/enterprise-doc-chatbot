from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import asyncio
import aiofiles
from typing import List, Optional
import logging
from dotenv import load_dotenv
import requests

from services.ollama_service_enhanced import EnhancedOllamaService
from services.document_service import DocumentService
from services.vector_store import VectorStore
from models.schemas import ChatRequest, ChatResponse, DocumentUploadResponse

# Load environment variables
load_dotenv()

# Reranker configuration
RERANKER_URL = os.getenv("RERANKER_URL", "http://localhost:8080/rerank")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Enterprise Document Chatbot",
    description="A chatbot that can answer questions about uploaded documents using Ollama",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
ollama_service = EnhancedOllamaService()
document_service = DocumentService()
vector_store = VectorStore()

# Ensure upload directory exists
upload_dir = os.getenv("UPLOAD_DIRECTORY", "./uploads")
os.makedirs(upload_dir, exist_ok=True)

def rerank_candidates_sync(query: str, candidates: list, top_k: int = 5):
    """Synchronous call to reranker service used from async endpoint"""
    # Convert DocumentChunk objects to format expected by reranker
    candidate_list = []
    for i, chunk in enumerate(candidates):
        candidate_list.append({
            "id": f"chunk_{i}",
            "text": chunk.content,
            "metadata": chunk.metadata if hasattr(chunk, 'metadata') and chunk.metadata else {}
        })

    payload = {
        "query": query,
        "candidates": candidate_list,
        "top_k": top_k
    }

    try:
        resp = requests.post(RERANKER_URL, json=payload, timeout=20)
        resp.raise_for_status()
        reranked_results = resp.json()

        # Convert back to original chunk format with reranker scores
        reranked_chunks = []
        for result in reranked_results:
            chunk_idx = int(result["id"].split("_")[1])
            original_chunk = candidates[chunk_idx]

            # Update similarity score with reranker score
            original_chunk.similarity_score = float(result["score"])
            # Add reranker metadata
            if hasattr(original_chunk, 'metadata') and original_chunk.metadata:
                original_chunk.metadata["reranker_score"] = float(result["score"])
                original_chunk.metadata["reranking_method"] = "cross_encoder"

            reranked_chunks.append(original_chunk)

        logger.info(f"Reranker processed {len(candidates)} candidates, returned top {len(reranked_chunks)}")
        return reranked_chunks

    except Exception as e:
        # fallback: return input candidates truncated
        logger.warning(f"Reranker failure: {e} — falling back to first {top_k} candidates")
        return candidates[:top_k]

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up Enterprise Document Chatbot")
    await vector_store.initialize()
    logger.info("Vector store initialized")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Enterprise Document Chatbot API is running"}

@app.get("/health")
async def health_check():
    """Health check with service status"""
    try:
        ollama_status = await ollama_service.check_health()
        return {
            "status": "healthy",
            "ollama_service": "connected" if ollama_status else "disconnected",
            "vector_store": "initialized"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
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

        # Check file size
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", 50)) * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )

        # Save file
        file_path = os.path.join(upload_dir, file.filename)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # Process document
        chunks = await document_service.process_document(file_path)

        # Store in vector database
        doc_id = await vector_store.add_document(file.filename, chunks)

        logger.info(f"Successfully processed document: {file.filename}")

        return DocumentUploadResponse(
            success=True,
            document_id=doc_id,
            filename=file.filename,
            chunks_created=len(chunks),
            message="Document uploaded and processed successfully"
        )

    except Exception as e:
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the document chatbot"""
    try:
        # Fetch a broader candidate set for reranking (50 candidates)
        candidates = await vector_store.search(request.message, limit=50)

        # Call cross-encoder reranker to get top 5 most relevant chunks
        top_chunks = await asyncio.get_event_loop().run_in_executor(
            None, rerank_candidates_sync, request.message, candidates, 5
        )

        # Generate response using Ollama with reranked chunks
        response = await ollama_service.generate_response(
            question=request.message,
            context_chunks=top_chunks,
            conversation_history=request.conversation_history
        )

        # Handle enhanced service response format
        if isinstance(response, dict):
            # Enhanced service returns a dictionary
            return ChatResponse(
                response=response["response"],
                sources=response.get("sources", top_chunks)[:5],  # Return top 5 sources
                success=True
            )
        else:
            # Fallback for simple string response
            return ChatResponse(
                response=response,
                sources=top_chunks[:5],  # Return top 5 reranked sources
                success=True
            )

    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        documents = await vector_store.list_documents()
        return {"documents": documents}
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from the vector store"""
    try:
        success = await vector_store.delete_document(document_id)
        if success:
            return {"message": "Document deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)