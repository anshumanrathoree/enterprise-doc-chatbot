import os
import asyncio
from typing import List, Dict, Any
import logging
from pathlib import Path
import aiofiles

# Document processing imports
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self):
        # Optimized chunking parameters (500-1000 tokens ≈ 2000-4000 characters)
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 3000))  # ~750 tokens
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", 900))  # 30% overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ";", ":", " ", ""],  # Better splitting
            keep_separator=True  # Preserve context at boundaries
        )

    async def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a document and return chunks with metadata"""
        try:
            file_extension = Path(file_path).suffix.lower()
            filename = Path(file_path).name

            # Extract text based on file type
            if file_extension == '.pdf':
                text = await self._extract_pdf_text(file_path)
            elif file_extension in ['.txt', '.md']:
                text = await self._extract_text_file(file_path)
            elif file_extension in ['.doc', '.docx']:
                text = await self._extract_doc_text(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")

            if not text or len(text.strip()) < 10:
                raise ValueError("Document appears to be empty or too short")

            # Split text into chunks
            documents = [Document(page_content=text, metadata={"filename": filename})]
            chunks = self.text_splitter.split_documents(documents)

            # Convert to our format
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                processed_chunks.append({
                    "content": chunk.page_content,
                    "metadata": {
                        "filename": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "file_path": file_path,
                        "file_type": file_extension,
                        "chunk_size": len(chunk.page_content)
                    }
                })

            logger.info(f"Successfully processed {filename}: {len(processed_chunks)} chunks created")
            return processed_chunks

        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            raise

    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file with page metadata"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()

                    # Add page boundary markers for better chunking
                    if page_text.strip():
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text.strip() + "\n"

            return text.strip()

        except Exception as e:
            logger.error(f"Error extracting PDF text from {file_path}: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    async def _extract_text_file(self, file_path: str) -> str:
        """Extract text from plain text file"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                text = await file.read()
            return text.strip()

        except UnicodeDecodeError:
            # Try with different encoding
            try:
                async with aiofiles.open(file_path, 'r', encoding='latin-1') as file:
                    text = await file.read()
                return text.strip()
            except Exception as e:
                logger.error(f"Error reading text file {file_path}: {str(e)}")
                raise ValueError(f"Failed to read text file: {str(e)}")

        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise ValueError(f"Failed to extract text: {str(e)}")

    async def _extract_doc_text(self, file_path: str) -> str:
        """Extract text from Word document (placeholder - requires python-docx)"""
        # For now, we'll skip Word document support
        # To implement, install python-docx and use:
        # from docx import Document
        # doc = Document(file_path)
        # return "\n".join([paragraph.text for paragraph in doc.paragraphs])

        raise ValueError("Word document support not yet implemented. Please convert to PDF or text file.")

    async def get_document_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic information about a document"""
        try:
            file_stat = os.stat(file_path)
            file_extension = Path(file_path).suffix.lower()
            filename = Path(file_path).name

            info = {
                "filename": filename,
                "file_path": file_path,
                "file_type": file_extension,
                "size_bytes": file_stat.st_size,
                "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                "created_at": file_stat.st_ctime,
                "modified_at": file_stat.st_mtime
            }

            # Try to get page count for PDFs
            if file_extension == '.pdf':
                try:
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        info["page_count"] = len(pdf_reader.pages)
                except:
                    info["page_count"] = "unknown"

            return info

        except Exception as e:
            logger.error(f"Error getting document info for {file_path}: {str(e)}")
            raise

    def validate_file(self, file_path: str, max_size_mb: int = 50) -> bool:
        """Validate if file can be processed"""
        try:
            if not os.path.exists(file_path):
                return False

            file_extension = Path(file_path).suffix.lower()
            allowed_extensions = ['.pdf', '.txt', '.md', '.doc', '.docx']

            if file_extension not in allowed_extensions:
                return False

            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > max_size_mb:
                return False

            return True

        except Exception:
            return False