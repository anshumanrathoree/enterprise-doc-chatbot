import ollama
import asyncio
import os
from typing import List, Optional, Dict, Any
import logging
from models.schemas import DocumentChunk, ChatMessage
from services.cache_service import cache_service

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        self.client = None

    async def check_health(self) -> bool:
        """Check if Ollama service is available"""
        try:
            # Initialize client if not already done
            if not self.client:
                self.client = ollama.AsyncClient(host=self.base_url)

            # Try to list models to check connectivity
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

            # Check if model exists
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

    async def generate_response(
        self,
        question: str,
        context_chunks: List[DocumentChunk],
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> Dict[str, Any]:
        """Generate a response using Ollama based on the question and document context"""
        try:
            if not self.client:
                self.client = ollama.AsyncClient(host=self.base_url)

            # Ensure model is available
            if not await self.ensure_model_available():
                raise Exception(f"Model {self.model} is not available")

            # Build context from document chunks with enhanced metadata
            context_parts = []
            for i, chunk in enumerate(context_chunks):
                filename = chunk.metadata.get('filename', 'Unknown')
                chunk_idx = chunk.metadata.get('chunk_index', 'N/A')
                search_method = chunk.metadata.get('search_method', 'unknown')
                similarity_score = getattr(chunk, 'similarity_score', 0.0)

                context_parts.append(
                    f"[Source {i+1}] Document: {filename} (Part {chunk_idx}, Score: {similarity_score:.3f}, Method: {search_method})\n"
                    f"Content: {chunk.content}\n"
                )

            context = "\n".join(context_parts)

            # Build conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n=== RECENT CONVERSATION ===\n" + "\n".join([
                    f"{msg.role.capitalize()}: {msg.content}"
                    for msg in conversation_history[-4:]  # Last 4 messages for better context
                ]) + "\n=== END CONVERSATION ===\n"

            # Enhanced prompt with provenance and hallucination prevention
            system_prompt = """You are an enterprise document assistant. Answer questions using ONLY the provided document content below.

INSTRUCTIONS:
1. Base your answer ONLY on the information in the provided sources
2. If information is not found in the sources, say "I cannot find that information in the provided documents"
3. When referencing information, mention the source (e.g., "According to Document X...")
4. Be concise but complete in your response
5. Do not make assumptions or add information not present in the sources
6. If the question cannot be answered with the available sources, clearly state this

AVAILABLE SOURCES:
{context}

{conversation_context}

QUESTION: {question}

ANSWER (based only on the provided sources):"""

            prompt = system_prompt.format(
                context=context[:3000],  # Increased context for better accuracy
                conversation_context=conversation_context,
                question=question
            )

            # Generate response with timeout
            try:
                response = await asyncio.wait_for(
                    self.client.generate(
                        model=self.model,
                        prompt=prompt,
                        options={
                            "temperature": 0.1,  # Lower for more factual responses
                            "top_p": 0.9,
                            "num_predict": 300,  # Allow more comprehensive answers
                            "top_k": 40,  # Better vocabulary for detailed responses
                            "repeat_penalty": 1.1,
                            "stop": ["QUESTION:", "AVAILABLE SOURCES:", "INSTRUCTIONS:"]  # Better stop tokens
                        }
                    ),
                    timeout=45.0  # Increased timeout to 45 seconds
                )
            except asyncio.TimeoutError:
                logger.warning("Ollama generation timed out, providing fallback response")
                # Generate a response based on the context chunks
                context_summary = "\n".join([chunk.content[:100] + "..." for chunk in context_chunks[:2]])
                return f"Based on the document content, I found relevant information: {context_summary}. However, I'm experiencing issues with the AI model response generation. Please try again or check the Ollama service."

            return response['response'].strip()

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}")

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