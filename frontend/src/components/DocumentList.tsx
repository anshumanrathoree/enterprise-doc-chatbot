import React, { useState, useEffect } from 'react';
import { listDocuments, deleteDocument, Document } from '../services/api';
import { FileText, Trash2, RefreshCw, Database } from 'lucide-react';

export const DocumentList: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listDocuments();
      setDocuments(response.documents);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDelete = async (documentId: string, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeletingId(documentId);
      await deleteDocument(documentId);
      setDocuments(prev => prev.filter(doc => doc.document_id !== documentId));
    } catch (err: any) {
      setError(err.message || 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const getFileTypeColor = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case '.pdf':
        return 'bg-red-100 text-red-800';
      case '.txt':
        return 'bg-gray-100 text-gray-800';
      case '.doc':
      case '.docx':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mr-3" />
          <span className="text-gray-600">Loading documents...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Document Management</h2>
        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {documents.length === 0 ? (
        <div className="text-center py-12">
          <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No documents uploaded</h3>
          <p className="text-gray-600 mb-4">
            Upload your first document to get started with the chatbot.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {documents.map((document) => (
            <div
              key={document.document_id}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center flex-1 min-w-0">
                  <FileText className="w-8 h-8 text-gray-400 mr-4 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-medium text-gray-900 truncate">
                      {document.filename}
                    </h3>
                    <div className="flex items-center mt-1 space-x-4 text-sm text-gray-500">
                      <span className="flex items-center">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getFileTypeColor(
                            document.file_type
                          )} mr-2`}
                        >
                          {document.file_type.toUpperCase().replace('.', '')}
                        </span>
                      </span>
                      <span>{document.chunk_count} chunks</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center ml-4">
                  <button
                    onClick={() => handleDelete(document.document_id, document.filename)}
                    disabled={deletingId === document.document_id}
                    className="flex items-center px-3 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deletingId === document.document_id ? (
                      <RefreshCw className="w-4 h-4 animate-spin mr-1" />
                    ) : (
                      <Trash2 className="w-4 h-4 mr-1" />
                    )}
                    {deletingId === document.document_id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>

              {/* Additional Document Info */}
              <div className="mt-3 pt-3 border-t border-gray-100">
                <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                  <div>
                    <span className="font-medium">Document ID:</span>
                    <span className="ml-1 font-mono text-xs">{document.document_id}</span>
                  </div>
                  <div>
                    <span className="font-medium">File Type:</span>
                    <span className="ml-1">{document.file_type}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {documents.length > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Summary</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Total Documents:</span>
                <span className="ml-2 font-medium text-gray-900">{documents.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Total Chunks:</span>
                <span className="ml-2 font-medium text-gray-900">
                  {documents.reduce((sum, doc) => sum + doc.chunk_count, 0)}
                </span>
              </div>
              <div>
                <span className="text-gray-500">File Types:</span>
                <span className="ml-2 font-medium text-gray-900">
                  {Array.from(new Set(documents.map(doc => doc.file_type))).join(', ')}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};