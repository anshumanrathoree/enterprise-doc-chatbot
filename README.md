# Enterprise Document Chatbot

A powerful document chatbot application that uses **Ollama** for local AI inference instead of cloud-based APIs like Claude or OpenAI. Upload documents (PDF, TXT, DOC, DOCX) and chat with them using natural language queries.

## Features

- **🤖 Local AI with Ollama**: No API keys required, runs completely offline
- **📄 Multi-format Support**: Upload PDF, TXT, DOC, and DOCX files
- **🔍 Intelligent Search**: Vector-based document search with ChromaDB
- **💬 Chat Interface**: Natural conversation with your documents
- **📊 Document Management**: Upload, list, and delete documents
- **⚡ Real-time Processing**: Fast document chunking and embedding
- **🏥 Health Monitoring**: System status dashboard

## Architecture

- **Frontend**: React with TypeScript, TailwindCSS
- **Backend**: FastAPI (Python)
- **AI Model**: Ollama (Local LLM)
- **Vector Database**: ChromaDB
- **Document Processing**: LangChain + PyPDF2

## Prerequisites

1. **Python 3.8+**
2. **Node.js 16+**
3. **Ollama** - [Install from here](https://ollama.ai/)

## Quick Start

### 1. Install Ollama

```bash
# Download and install Ollama from https://ollama.ai/
# Then pull a model (e.g., llama2)
ollama pull llama2
```

### 2. Setup Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py
```

The backend will start on `http://localhost:8000`

### 3. Setup Frontend

```bash
cd frontend
npm install
npm start
```

The frontend will start on `http://localhost:3000`

### 4. Start Using

1. Open http://localhost:3000
2. Go to "Upload Documents" and upload a PDF/TXT file
3. Switch to "Chat" and ask questions about your document
4. Monitor system health in "System Health" tab

## Configuration

### Backend Environment Variables (.env)

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
CHROMA_PERSIST_DIRECTORY=./chroma_db
UPLOAD_DIRECTORY=./uploads
MAX_FILE_SIZE_MB=50
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Supported Ollama Models

- `llama2` (default)
- `mistral`
- `codellama`
- `neural-chat`

Change the model in `.env`:
```env
OLLAMA_MODEL=mistral
```

## API Endpoints

### Health Check
- `GET /health` - System health status

### Document Operations
- `POST /upload` - Upload document
- `GET /documents` - List documents
- `DELETE /documents/{id}` - Delete document

### Chat
- `POST /chat` - Send message to chatbot

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Tests

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

## Docker Support

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Troubleshooting

### Ollama Issues

1. **Ollama not found**: Make sure Ollama is installed and running
   ```bash
   ollama serve
   ```

2. **Model not available**: Pull the required model
   ```bash
   ollama pull llama2
   ```

### Backend Issues

1. **Port conflicts**: Change the port in `main.py`
2. **Dependencies**: Reinstall requirements
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

### Frontend Issues

1. **CORS errors**: Make sure backend is running on port 8000
2. **Build errors**: Clear cache and reinstall
   ```bash
   npm cache clean --force
   rm -rf node_modules package-lock.json
   npm install
   ```

## Performance Tips

1. **Model Selection**: Use smaller models for faster responses:
   - `phi` - Very fast, good for simple queries
   - `llama2:7b` - Balanced speed/quality
   - `llama2:13b` - Better quality, slower

2. **Chunking**: Adjust chunk size in `.env` for your documents:
   - Smaller chunks (500-800): Better for specific questions
   - Larger chunks (1000-1500): Better for context

3. **Hardware**: Ollama runs better with:
   - 16GB+ RAM
   - GPU acceleration (CUDA/Metal)

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request