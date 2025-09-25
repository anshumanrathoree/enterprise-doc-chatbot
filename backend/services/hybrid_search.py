import os
import asyncio
from typing import List, Dict, Any, Tuple
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import re
from models.schemas import DocumentChunk

logger = logging.getLogger(__name__)

class HybridSearchService:
    def __init__(self):
        self.embedding_model = None
        self.bm25_index = None
        self.document_chunks = []  # Store all chunks for BM25 indexing
        self.chunk_embeddings = []  # Store precomputed embeddings
        self.is_initialized = False

    async def initialize(self):
        """Initialize the hybrid search service with embedding model"""
        try:
            # Initialize sentence transformer for semantic search
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.is_initialized = True
            logger.info("Hybrid search service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing hybrid search service: {str(e)}")
            raise

    def _preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for BM25 tokenization"""
        # Convert to lowercase and split by whitespace and punctuation
        text = text.lower()
        # Remove extra whitespace and split
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    async def index_documents(self, chunks: List[DocumentChunk]):
        """Index document chunks for both BM25 and semantic search"""
        try:
            if not self.is_initialized:
                await self.initialize()

            logger.info(f"Indexing {len(chunks)} document chunks for hybrid search")

            # Store chunks
            self.document_chunks = chunks

            # Prepare texts for BM25
            tokenized_docs = []
            texts_for_embedding = []

            for chunk in chunks:
                # Tokenize for BM25
                tokens = self._preprocess_text(chunk.content)
                tokenized_docs.append(tokens)

                # Store text for embedding
                texts_for_embedding.append(chunk.content)

            # Build BM25 index
            self.bm25_index = BM25Okapi(tokenized_docs)
            logger.info("BM25 index built successfully")

            # Generate embeddings for all chunks
            logger.info("Generating embeddings for semantic search...")
            self.chunk_embeddings = self.embedding_model.encode(
                texts_for_embedding,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            logger.info(f"Generated {len(self.chunk_embeddings)} embeddings")

        except Exception as e:
            logger.error(f"Error indexing documents for hybrid search: {str(e)}")
            raise

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        bm25_weight: float = 0.4,
        semantic_weight: float = 0.6,
        bm25_candidates: int = 20
    ) -> List[DocumentChunk]:
        """
        Perform hybrid search combining BM25 and semantic similarity

        Args:
            query: Search query
            limit: Number of results to return
            bm25_weight: Weight for BM25 scores (0-1)
            semantic_weight: Weight for semantic scores (0-1)
            bm25_candidates: Number of candidates to get from BM25 before semantic reranking
        """
        try:
            if not self.bm25_index or not self.document_chunks:
                logger.warning("No documents indexed for hybrid search")
                return []

            # Step 1: BM25 sparse search to get initial candidates
            tokenized_query = self._preprocess_text(query)
            bm25_scores = self.bm25_index.get_scores(tokenized_query)

            # Get top BM25 candidates
            bm25_indices = np.argsort(bm25_scores)[::-1][:bm25_candidates]

            logger.info(f"BM25 found {len(bm25_indices)} candidates")

            # Step 2: Semantic search on BM25 candidates
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0]

            # Calculate semantic similarities for BM25 candidates
            candidate_scores = []
            for idx in bm25_indices:
                if idx < len(self.chunk_embeddings):
                    # Get semantic similarity
                    chunk_embedding = self.chunk_embeddings[idx]
                    semantic_score = np.dot(query_embedding, chunk_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                    )

                    # Normalize BM25 score (BM25 scores can vary widely)
                    bm25_score = bm25_scores[idx]
                    normalized_bm25 = min(bm25_score / 10.0, 1.0)  # Simple normalization

                    # Combine scores
                    hybrid_score = (
                        bm25_weight * normalized_bm25 +
                        semantic_weight * semantic_score
                    )

                    candidate_scores.append((idx, hybrid_score, semantic_score, normalized_bm25))

            # Step 3: Sort by hybrid score and return top results
            candidate_scores.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, hybrid_score, semantic_score, bm25_score in candidate_scores[:limit]:
                chunk = self.document_chunks[idx]

                # Create a copy with updated similarity score
                result_chunk = DocumentChunk(
                    content=chunk.content,
                    metadata=chunk.metadata.copy(),
                    similarity_score=float(hybrid_score)  # Convert numpy.float32 to Python float
                )

                # Add search method info to metadata
                result_chunk.metadata["search_method"] = "hybrid"
                result_chunk.metadata["bm25_score"] = round(float(bm25_score), 4)
                result_chunk.metadata["semantic_score"] = round(float(semantic_score), 4)
                result_chunk.metadata["hybrid_score"] = round(float(hybrid_score), 4)

                results.append(result_chunk)

            logger.info(f"Hybrid search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            return []

    async def semantic_search_only(self, query: str, limit: int = 10) -> List[DocumentChunk]:
        """Perform pure semantic search for comparison"""
        try:
            if not self.chunk_embeddings or not self.document_chunks:
                return []

            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0]

            similarities = []
            for i, chunk_embedding in enumerate(self.chunk_embeddings):
                similarity = np.dot(query_embedding, chunk_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                )
                similarities.append((i, similarity))

            # Sort by similarity and get top results
            similarities.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, similarity in similarities[:limit]:
                chunk = self.document_chunks[idx]
                result_chunk = DocumentChunk(
                    content=chunk.content,
                    metadata=chunk.metadata.copy(),
                    similarity_score=float(similarity)  # Convert numpy.float32 to Python float
                )
                result_chunk.metadata["search_method"] = "semantic_only"
                results.append(result_chunk)

            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []

    async def bm25_search_only(self, query: str, limit: int = 10) -> List[DocumentChunk]:
        """Perform pure BM25 search for comparison"""
        try:
            if not self.bm25_index or not self.document_chunks:
                return []

            tokenized_query = self._preprocess_text(query)
            bm25_scores = self.bm25_index.get_scores(tokenized_query)

            # Get top results
            top_indices = np.argsort(bm25_scores)[::-1][:limit]

            results = []
            for idx in top_indices:
                chunk = self.document_chunks[idx]
                normalized_score = min(bm25_scores[idx] / 10.0, 1.0)

                result_chunk = DocumentChunk(
                    content=chunk.content,
                    metadata=chunk.metadata.copy(),
                    similarity_score=normalized_score
                )
                result_chunk.metadata["search_method"] = "bm25_only"
                result_chunk.metadata["bm25_raw_score"] = bm25_scores[idx]
                results.append(result_chunk)

            return results

        except Exception as e:
            logger.error(f"Error in BM25 search: {str(e)}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed documents"""
        return {
            "total_chunks": len(self.document_chunks),
            "has_bm25_index": self.bm25_index is not None,
            "has_embeddings": len(self.chunk_embeddings) > 0,
            "is_initialized": self.is_initialized
        }