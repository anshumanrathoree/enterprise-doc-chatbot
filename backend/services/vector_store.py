import os
import uuid
import asyncio
from typing import List, Dict, Any, Optional
import logging
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import numpy as np
from models.schemas import DocumentChunk
from services.hybrid_search import HybridSearchService
from services.reranker import Reranker

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
        self.collection_name = "documents"
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.hybrid_search = HybridSearchService()
        self.use_hybrid_search = os.getenv("USE_HYBRID_SEARCH", "true").lower() == "true"
        self.reranker = Reranker()
        self.use_reranker = os.getenv("USE_RERANKER", "true").lower() == "true"

    async def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Create or get collection
            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function
                )
                logger.info("Connected to existing collection")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function,
                    metadata={"description": "Document chunks for enterprise chatbot"}
                )
                logger.info("Created new collection")

            # Initialize hybrid search service
            if self.use_hybrid_search:
                await self.hybrid_search.initialize()
                logger.info("Hybrid search service initialized")

            # Initialize reranker service
            if self.use_reranker:
                await self.reranker.initialize()
                logger.info("Reranker service initialized")

            # Initialize hybrid search with existing documents
            if self.use_hybrid_search:
                await self._initialize_hybrid_search()

        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    async def _initialize_hybrid_search(self):
        """Initialize hybrid search with existing documents from ChromaDB"""
        try:
            # Get all existing chunks from ChromaDB
            all_chunks = await self._get_all_chunks_for_hybrid_search()

            if all_chunks:
                await self.hybrid_search.index_documents(all_chunks)
                logger.info(f"Hybrid search initialized with {len(all_chunks)} existing documents")
            else:
                logger.info("No existing documents found for hybrid search initialization")

        except Exception as e:
            logger.error(f"Error initializing hybrid search: {str(e)}")
            # Continue without hybrid search if initialization fails
            self.use_hybrid_search = False

    async def add_document(self, filename: str, chunks: List[Dict[str, Any]]) -> str:
        """Add document chunks to the vector store"""
        try:
            if not self.collection:
                await self.initialize()

            document_id = str(uuid.uuid4())

            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_{i}"

                documents.append(chunk["content"])

                # Prepare metadata (ChromaDB requires string values)
                metadata = {
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": str(chunk["metadata"]["chunk_index"]),
                    "total_chunks": str(chunk["metadata"]["total_chunks"]),
                    "file_type": chunk["metadata"]["file_type"],
                    "chunk_size": str(chunk["metadata"]["chunk_size"])
                }

                metadatas.append(metadata)
                ids.append(chunk_id)

            # Add to collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            # Update hybrid search index if enabled
            if self.use_hybrid_search:
                # Get all existing chunks to rebuild the hybrid search index
                all_chunks = await self._get_all_chunks_for_hybrid_search()
                await self.hybrid_search.index_documents(all_chunks)
                logger.info("Updated hybrid search index")

            logger.info(f"Added {len(chunks)} chunks for document {filename}")
            return document_id

        except Exception as e:
            logger.error(f"Error adding document to vector store: {str(e)}")
            raise

    async def search(self, query: str, limit: int = 5) -> List[DocumentChunk]:
        """Search for relevant document chunks using hybrid search if enabled"""
        try:
            if not self.collection:
                await self.initialize()

            # Use hybrid search if enabled and available
            if self.use_hybrid_search and self.hybrid_search.is_initialized:
                chunks = await self.hybrid_search.hybrid_search(
                    query=query,
                    limit=limit * 2 if self.use_reranker else limit,  # Get more candidates if reranking
                    bm25_weight=0.4,
                    semantic_weight=0.6,
                    bm25_candidates=min(20, limit * 4)  # Get more candidates for better reranking
                )
                logger.info(f"Hybrid search found {len(chunks)} relevant chunks")

                # Apply reranker if enabled
                if self.use_reranker and self.reranker.is_initialized and len(chunks) > 1:
                    chunks = await self.reranker.rerank_with_fusion(
                        query=query,
                        chunks=chunks,
                        top_k=limit
                    )
                    logger.info(f"Reranker refined results to {len(chunks)} chunks")

                return chunks

            # Fallback to ChromaDB semantic search
            chunks = await self._chromadb_search(query, limit * 2 if self.use_reranker else limit)

            # Apply reranker to ChromaDB results if enabled
            if self.use_reranker and self.reranker.is_initialized and len(chunks) > 1:
                chunks = await self.reranker.rerank_chunks(query=query, chunks=chunks, top_k=limit)
                logger.info(f"Reranker refined ChromaDB results to {len(chunks)} chunks")

            return chunks

        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            # Fallback to ChromaDB search on error
            return await self._chromadb_search(query, limit)

    async def _chromadb_search(self, query: str, limit: int = 5) -> List[DocumentChunk]:
        """Fallback ChromaDB semantic search"""
        try:
            # Query the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )

            # Convert results to DocumentChunk objects
            chunks = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    content = results['documents'][0][i]
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if results['distances'] else 0

                    # Convert similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 - distance if distance else 1.0

                    chunk = DocumentChunk(
                        content=content,
                        metadata={
                            "filename": metadata.get("filename", ""),
                            "chunk_index": int(metadata.get("chunk_index", 0)),
                            "document_id": metadata.get("document_id", ""),
                            "file_type": metadata.get("file_type", ""),
                            "chunk_size": int(metadata.get("chunk_size", 0))
                        },
                        similarity_score=similarity_score
                    )
                    chunk.metadata["search_method"] = "chromadb_only"
                    chunks.append(chunk)

            logger.info(f"ChromaDB search found {len(chunks)} relevant chunks")
            return chunks

        except Exception as e:
            logger.error(f"Error in ChromaDB search: {str(e)}")
            return []

    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the vector store"""
        try:
            if not self.collection:
                await self.initialize()

            # Get all documents
            results = self.collection.get()

            # Group by document_id
            documents = {}
            for i, metadata in enumerate(results['metadatas']):
                doc_id = metadata.get("document_id")
                filename = metadata.get("filename")

                if doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": filename,
                        "chunk_count": 0,
                        "file_type": metadata.get("file_type", ""),
                    }

                documents[doc_id]["chunk_count"] += 1

            return list(documents.values())

        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            return []

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks"""
        try:
            if not self.collection:
                await self.initialize()

            # Get all chunk IDs for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )

            if not results['ids']:
                logger.warning(f"Document {document_id} not found")
                return False

            # Delete all chunks
            self.collection.delete(ids=results['ids'])

            logger.info(f"Deleted document {document_id} with {len(results['ids'])} chunks")
            return True

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False

    async def get_document_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a specific document"""
        try:
            if not self.collection:
                await self.initialize()

            results = self.collection.get(
                where={"document_id": document_id}
            )

            chunks = []
            for i, content in enumerate(results['documents']):
                metadata = results['metadatas'][i]

                chunk = DocumentChunk(
                    content=content,
                    metadata={
                        "filename": metadata.get("filename", ""),
                        "chunk_index": int(metadata.get("chunk_index", 0)),
                        "document_id": metadata.get("document_id", ""),
                        "file_type": metadata.get("file_type", ""),
                        "chunk_size": int(metadata.get("chunk_size", 0))
                    }
                )
                chunks.append(chunk)

            # Sort by chunk index
            chunks.sort(key=lambda x: x.metadata["chunk_index"])
            return chunks

        except Exception as e:
            logger.error(f"Error getting document chunks: {str(e)}")
            return []

    async def clear_all(self):
        """Clear all documents from the vector store"""
        try:
            if not self.collection:
                await self.initialize()

            # Delete the collection and recreate it
            self.client.delete_collection(self.collection_name)

            embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=embedding_function,
                metadata={"description": "Document chunks for enterprise chatbot"}
            )

            logger.info("Cleared all documents from vector store")
            return True

        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
            return False

    async def _get_all_chunks_for_hybrid_search(self) -> List[DocumentChunk]:
        """Get all chunks from ChromaDB for hybrid search indexing"""
        try:
            if not self.collection:
                await self.initialize()

            # Get all documents from ChromaDB
            results = self.collection.get()

            chunks = []
            for i, content in enumerate(results['documents']):
                metadata = results['metadatas'][i]

                chunk = DocumentChunk(
                    content=content,
                    metadata={
                        "filename": metadata.get("filename", ""),
                        "chunk_index": int(metadata.get("chunk_index", 0)),
                        "document_id": metadata.get("document_id", ""),
                        "file_type": metadata.get("file_type", ""),
                        "chunk_size": int(metadata.get("chunk_size", 0))
                    }
                )
                chunks.append(chunk)

            logger.info(f"Retrieved {len(chunks)} chunks for hybrid search indexing")
            return chunks

        except Exception as e:
            logger.error(f"Error getting all chunks for hybrid search: {str(e)}")
            return []