import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
}

export interface DocumentChunk {
  content: string;
  metadata: {
    filename: string;
    chunk_index: number;
    document_id: string;
    file_type: string;
    chunk_size: number;
  };
  similarity_score?: number;
}

export interface ChatResponse {
  response: string;
  sources?: DocumentChunk[];
  success: boolean;
}

export interface DocumentUploadResponse {
  success: boolean;
  document_id: string;
  filename: string;
  chunks_created: number;
  message: string;
}

export interface Document {
  document_id: string;
  filename: string;
  chunk_count: number;
  file_type: string;
}

export interface HealthResponse {
  status: string;
  ollama_service: string;
  vector_store: string;
  error?: string;
}

// API functions
export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await api.get('/health');
  return response.data;
};

export const uploadDocument = async (file: File): Promise<DocumentUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

export const sendMessage = async (chatRequest: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post('/chat', chatRequest);
  return response.data;
};

export const listDocuments = async (): Promise<{ documents: Document[] }> => {
  const response = await api.get('/documents');
  return response.data;
};

export const deleteDocument = async (documentId: string): Promise<{ message: string }> => {
  const response = await api.delete(`/documents/${documentId}`);
  return response.data;
};

// Error handling interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);

    if (error.response?.status === 500) {
      throw new Error('Server error occurred. Please try again.');
    } else if (error.response?.status === 404) {
      throw new Error('Resource not found.');
    } else if (error.code === 'ECONNREFUSED') {
      throw new Error('Cannot connect to server. Please ensure the backend is running.');
    }

    throw error;
  }
);