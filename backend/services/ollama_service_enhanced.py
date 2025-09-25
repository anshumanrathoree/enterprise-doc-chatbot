import ollama
import asyncio
import os
from typing import List, Optional, Dict, Any
import logging
from models.schemas import DocumentChunk, ChatMessage
from services.cache_service import cache_service
import re

logger = logging.getLogger(__name__)

class EnhancedOllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        self.client = None

    async def check_health(self) -> bool:
        """Check if Ollama service is available"""
        try:
            if not self.client:
                self.client = ollama.AsyncClient(host=self.base_url)
            models = await self.client.list()
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False

    async def ensure_model_available(self) -> bool:
        """Ensure the specified model is available, pull if necessary"""
        try:
            if not self.client:
                self.client = ollama.AsyncClient(host=self.base_url)

            models = await self.client.list()
            model_names = [model['name'] for model in models.get('models', [])]

            if self.model not in model_names:
                logger.info(f"Model {self.model} not found. Attempting to pull...")
                await self.client.pull(self.model)
                logger.info(f"Successfully pulled model {self.model}")

            return True
        except Exception as e:
            logger.error(f"Failed to ensure model availability: {str(e)}")
            return False

    def _calculate_confidence_score(self, response: str, context_chunks: List[DocumentChunk]) -> float:
        """Calculate confidence score based on response grounding"""
        try:
            # Check for "cannot find" or similar phrases (low confidence)
            if re.search(r"(cannot find|don't have|not available|not mentioned)", response.lower()):
                return 0.2

            # Check for source citations (high confidence)
            source_citations = len(re.findall(r"(according to|source|document)", response.lower()))

            # Check content overlap with sources
            response_words = set(response.lower().split())
            context_words = set()
            for chunk in context_chunks:
                context_words.update(chunk.content.lower().split())

            overlap_ratio = len(response_words.intersection(context_words)) / len(response_words) if response_words else 0

            # Combined confidence score
            confidence = min(1.0, (overlap_ratio * 0.7) + (source_citations * 0.1) + 0.2)
            return round(confidence, 3)

        except Exception:
            return 0.5

    def _generate_fallback_response(self, context_chunks: List[DocumentChunk], question: str) -> str:
        """Generate a fallback response when the model fails"""
        if not context_chunks:
            return "I don't have any relevant documents to answer your question. Please upload some documents first."

        # Extract key information from chunks
        relevant_snippets = []
        for i, chunk in enumerate(context_chunks[:2]):  # Top 2 chunks
            snippet = chunk.content[:150].strip()
            if snippet:
                relevant_snippets.append(f"From {chunk.metadata.get('filename', 'document')} (Part {chunk.metadata.get('chunk_index', 'N/A')}): {snippet}...")

        if relevant_snippets:
            return f"Based on the document content, here's what I found:\n\n" + "\n\n".join(relevant_snippets) + "\n\nPlease note: The AI model is currently experiencing issues. The above information is extracted directly from your documents."

        return "I found relevant documents but am experiencing technical issues with response generation. Please try again."

    async def generate_response(
        self,
        question: str,
        context_chunks: List[DocumentChunk],
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> Dict[str, Any]:
        """Generate a response using Ollama with caching and enhanced grounding"""
        try:
            # Check cache first
            cached_response = cache_service.get(question, context_chunks)
            if cached_response:
                logger.info("Returning cached response")
                cached_response["metadata"]["cached"] = True
                return cached_response

            if not self.client:
                self.client = ollama.AsyncClient(host=self.base_url)

            # Ensure model is available
            if not await self.ensure_model_available():
                raise Exception(f"Model {self.model} is not available")

            # Build context with enhanced provenance tracking
            context_parts = []
            source_references = []

            for i, chunk in enumerate(context_chunks):
                filename = chunk.metadata.get('filename', 'Unknown')
                chunk_idx = chunk.metadata.get('chunk_index', 'N/A')
                search_method = chunk.metadata.get('search_method', 'unknown')
                similarity_score = getattr(chunk, 'similarity_score', 0.0)

                source_id = f"Source_{i+1}"
                source_references.append({
                    "id": source_id,
                    "filename": filename,
                    "chunk_index": chunk_idx,
                    "similarity_score": similarity_score,
                    "search_method": search_method,
                    "content_preview": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                })

                context_parts.append(
                    f"[{source_id}] Document: {filename} (Part {chunk_idx}, Relevance: {similarity_score:.3f})\n"
                    f"Content: {chunk.content}\n"
                )

            context = "\n".join(context_parts)

            # Build conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n=== RECENT CONVERSATION ===\n" + "\n".join([
                    f"{msg.role.capitalize()}: {msg.content}"
                    for msg in conversation_history[-3:]  # Last 3 messages for context
                ]) + "\n=== END CONVERSATION ===\n"

            # Enhanced prompt with strict grounding
            system_prompt = """You are a precise enterprise document assistant. You MUST follow these rules:

STRICT RULES:
1. Answer ONLY using information from the provided sources below
2. If information is missing, respond with: "I cannot find that information in the provided documents"
3. ALWAYS cite sources when answering (e.g., "According to Source_1...")
4. Do NOT make assumptions or add external knowledge
5. If sources contradict each other, mention both viewpoints
6. Keep responses factual and concise

AVAILABLE SOURCES:
{context}

{conversation_context}

USER QUESTION: {question}

GROUNDED ANSWER (cite sources):"""

            prompt = system_prompt.format(
                context=context[:4000],  # Increased context for better accuracy
                conversation_context=conversation_context,
                question=question
            )

            # Generate response with optimized parameters
            try:
                start_time = asyncio.get_event_loop().time()
                response = await asyncio.wait_for(
                    self.client.generate(
                        model=self.model,
                        prompt=prompt,
                        stream=False,  # Disable streaming to avoid hangs
                        options={
                            "temperature": 0.05,  # Very low for maximum factuality
                            "top_p": 0.85,
                            "num_predict": 350,
                            "top_k": 30,
                            "repeat_penalty": 1.15,
                            "stop": ["USER QUESTION:", "AVAILABLE SOURCES:", "STRICT RULES:"]
                        }
                    ),
                    timeout=30.0  # Reduced timeout since we're not streaming
                )
                generation_time = asyncio.get_event_loop().time() - start_time

            except asyncio.TimeoutError:
                logger.warning("Ollama generation timed out")
                fallback_response = self._generate_fallback_response(context_chunks, question)

                # Cache fallback response with shorter TTL
                result = {
                    "response": fallback_response,
                    "sources": context_chunks,
                    "metadata": {
                        "cached": False,
                        "generation_time": 60.0,
                        "fallback": True,
                        "source_count": len(context_chunks),
                        "confidence_score": 0.3
                    }
                }
                cache_service.set(question, result, context_chunks, ttl=300)  # 5 minutes
                return result

            generated_text = response['response'].strip()

            # Enhanced answer validation and grounding check
            confidence_score = self._calculate_confidence_score(generated_text, context_chunks)

            # Create comprehensive response object
            result = {
                "response": generated_text,
                "sources": context_chunks,
                "metadata": {
                    "cached": False,
                    "generation_time": round(generation_time, 2),
                    "confidence_score": confidence_score,
                    "source_count": len(context_chunks),
                    "model": self.model,
                    "fallback": False
                },
                "source_references": source_references
            }

            # Cache successful response
            cache_service.set(question, result, context_chunks)

            return result

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Return error response with fallback
            fallback_response = self._generate_fallback_response(context_chunks, question)
            return {
                "response": fallback_response,
                "sources": context_chunks,
                "metadata": {
                    "cached": False,
                    "generation_time": 0,
                    "error": str(e),
                    "fallback": True,
                    "source_count": len(context_chunks),
                    "confidence_score": 0.2
                }
            }

    async def generate_summary(self, text: str) -> str:
        """Generate a summary of the given text"""
        try:
            if not self.client:
                self.client = ollama.AsyncClient(host=self.base_url)

            prompt = f"""Please provide a concise summary of the following text:

{text[:2000]}  # Limit text to avoid token limits

Summary:"""

            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "max_tokens": 200,
                }
            )

            return response['response'].strip()

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return "Summary unavailable"

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return cache_service.get_stats()