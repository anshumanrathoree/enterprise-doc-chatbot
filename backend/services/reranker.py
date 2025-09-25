import os
import asyncio
from typing import List, Tuple
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, util
from models.schemas import DocumentChunk

logger = logging.getLogger(__name__)

class Reranker:
    def __init__(self):
        self.model = None
        self.model_name = os.getenv("RERANKER_MODEL", "all-MiniLM-L6-v2")
        self.is_initialized = False

    async def initialize(self):
        """Initialize the reranker model"""
        try:
            # Use the same model as embeddings for consistency and efficiency
            self.model = SentenceTransformer(self.model_name)
            self.is_initialized = True
            logger.info(f"Reranker initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error initializing reranker: {str(e)}")
            raise

    async def rerank_chunks(
        self,
        query: str,
        chunks: List[DocumentChunk],
        top_k: int = None
    ) -> List[DocumentChunk]:
        """
        Rerank document chunks based on query-document similarity

        Args:
            query: The search query
            chunks: List of document chunks to rerank
            top_k: Number of top chunks to return (if None, return all reranked)

        Returns:
            List of reranked chunks with updated similarity scores
        """
        try:
            if not self.is_initialized:
                await self.initialize()

            if not chunks:
                return []

            # Extract content from chunks
            documents = [chunk.content for chunk in chunks]

            # Encode query and documents
            query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
            doc_embeddings = self.model.encode(documents, convert_to_numpy=True)

            # Calculate semantic similarities
            similarities = []
            for i, doc_embedding in enumerate(doc_embeddings):
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append((i, similarity))

            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Rerank chunks and update scores
            reranked_chunks = []
            for idx, (chunk_idx, similarity_score) in enumerate(similarities):
                original_chunk = chunks[chunk_idx]

                # Create a copy with updated similarity score
                reranked_chunk = DocumentChunk(
                    content=original_chunk.content,
                    metadata=original_chunk.metadata.copy(),
                    similarity_score=float(similarity_score)  # Convert numpy.float32 to Python float
                )

                # Add reranking metadata
                reranked_chunk.metadata["reranked_position"] = idx + 1
                reranked_chunk.metadata["original_position"] = chunk_idx + 1
                reranked_chunk.metadata["reranked_score"] = round(float(similarity_score), 4)  # Convert numpy.float32 to Python float
                reranked_chunk.metadata["reranking_method"] = "semantic_similarity"

                # Keep original score for comparison
                if hasattr(original_chunk, 'similarity_score'):
                    reranked_chunk.metadata["original_score"] = round(float(original_chunk.similarity_score), 4)  # Convert to Python float

                reranked_chunks.append(reranked_chunk)

            # Return top-k if specified
            if top_k:
                reranked_chunks = reranked_chunks[:top_k]

            logger.info(f"Reranked {len(chunks)} chunks, returning top {len(reranked_chunks)}")
            return reranked_chunks

        except Exception as e:
            logger.error(f"Error in reranking: {str(e)}")
            # Return original chunks if reranking fails
            return chunks

    async def score_relevance(self, query: str, document: str) -> float:
        """
        Score the relevance between a query and a document

        Args:
            query: The search query
            document: The document text

        Returns:
            Relevance score between 0 and 1
        """
        try:
            if not self.is_initialized:
                await self.initialize()

            # Encode query and document
            embeddings = self.model.encode([query, document], convert_to_numpy=True)

            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )

            # Ensure score is between 0 and 1
            return max(0.0, float(similarity))

        except Exception as e:
            logger.error(f"Error scoring relevance: {str(e)}")
            return 0.0

    async def rerank_with_fusion(
        self,
        query: str,
        chunks: List[DocumentChunk],
        fusion_weights: List[float] = None,
        top_k: int = None
    ) -> List[DocumentChunk]:
        """
        Advanced reranking using multiple scoring methods with fusion

        Args:
            query: The search query
            chunks: List of document chunks to rerank
            fusion_weights: Weights for combining different scores [original, semantic, length]
            top_k: Number of top chunks to return

        Returns:
            List of reranked chunks with fused scores
        """
        try:
            if not chunks:
                return []

            if fusion_weights is None:
                fusion_weights = [0.4, 0.5, 0.1]  # original, semantic, length_penalty

            # Get semantic scores from reranking
            semantic_ranked = await self.rerank_chunks(query, chunks, top_k=None)

            # Calculate additional scores
            fused_scores = []
            for i, chunk in enumerate(semantic_ranked):
                original_score = chunk.metadata.get("original_score", 0.5)
                semantic_score = chunk.similarity_score

                # Length penalty (prefer chunks of moderate length)
                chunk_length = len(chunk.content)
                optimal_length = 2000  # Around 500 tokens
                length_penalty = 1.0 - abs(chunk_length - optimal_length) / optimal_length
                length_penalty = max(0.1, min(1.0, length_penalty))

                # Fuse scores
                fused_score = (
                    fusion_weights[0] * original_score +
                    fusion_weights[1] * semantic_score +
                    fusion_weights[2] * length_penalty
                )

                fused_scores.append((i, fused_score, semantic_score, length_penalty))

            # Sort by fused score
            fused_scores.sort(key=lambda x: x[1], reverse=True)

            # Create final reranked list
            final_chunks = []
            for idx, (chunk_idx, fused_score, semantic_score, length_penalty) in enumerate(fused_scores):
                chunk = semantic_ranked[chunk_idx]

                # Update metadata with fusion information
                chunk.similarity_score = float(fused_score)  # Convert to Python float
                chunk.metadata["fusion_score"] = round(float(fused_score), 4)
                chunk.metadata["semantic_score"] = round(float(semantic_score), 4)
                chunk.metadata["length_penalty"] = round(float(length_penalty), 4)
                chunk.metadata["final_position"] = idx + 1
                chunk.metadata["reranking_method"] = "fusion_reranking"

                final_chunks.append(chunk)

            # Return top-k if specified
            if top_k:
                final_chunks = final_chunks[:top_k]

            logger.info(f"Fusion reranking completed, returning top {len(final_chunks)} chunks")
            return final_chunks

        except Exception as e:
            logger.error(f"Error in fusion reranking: {str(e)}")
            return chunks

    def get_stats(self) -> dict:
        """Get reranker statistics"""
        return {
            "model_name": self.model_name,
            "is_initialized": self.is_initialized,
        }