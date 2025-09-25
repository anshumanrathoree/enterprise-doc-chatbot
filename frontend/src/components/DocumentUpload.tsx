import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadDocument, DocumentUploadResponse } from '../services/api';
import { Upload, FileText, CheckCircle, AlertCircle, Loader } from 'lucide-react';

export const DocumentUpload: React.FC = () => {
  const [uploadStatus, setUploadStatus] = useState<{
    status: 'idle' | 'uploading' | 'success' | 'error';
    message: string;
    response?: DocumentUploadResponse;
  }>({
    status: 'idle',
    message: '',
  });

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];

    // Validate file type
    const allowedTypes = ['.pdf', '.txt', '.doc', '.docx'];
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!allowedTypes.includes(fileExtension)) {
      setUploadStatus({
        status: 'error',
        message: `File type ${fileExtension} not supported. Please upload PDF, TXT, DOC, or DOCX files.`,
      });
      return;
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      setUploadStatus({
        status: 'error',
        message: `File too large. Maximum size is 50MB. Your file is ${(file.size / (1024 * 1024)).toFixed(1)}MB.`,
      });
      return;
    }

    setUploadStatus({
      status: 'uploading',
      message: `Uploading ${file.name}...`,
    });

    try {
      const response = await uploadDocument(file);

      setUploadStatus({
        status: 'success',
        message: 'Document uploaded and processed successfully!',
        response,
      });
    } catch (error: any) {
      setUploadStatus({
        status: 'error',
        message: error.message || 'Failed to upload document. Please try again.',
      });
    }
  }, []);

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragReject,
  } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    disabled: uploadStatus.status === 'uploading',
  });

  const resetUpload = () => {
    setUploadStatus({
      status: 'idle',
      message: '',
    });
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Upload Documents</h2>

        {/* Upload Area */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            isDragActive && !isDragReject
              ? 'border-primary-400 bg-primary-50'
              : isDragReject
              ? 'border-red-400 bg-red-50'
              : uploadStatus.status === 'uploading'
              ? 'border-gray-300 bg-gray-50 cursor-not-allowed'
              : 'border-gray-300 hover:border-primary-400 hover:bg-primary-50'
          }`}
        >
          <input {...getInputProps()} />

          {uploadStatus.status === 'uploading' ? (
            <div className="flex flex-col items-center">
              <Loader className="w-12 h-12 text-primary-600 animate-spin mb-4" />
              <p className="text-lg font-medium text-gray-900">Processing Document...</p>
              <p className="text-sm text-gray-500 mt-1">{uploadStatus.message}</p>
            </div>
          ) : (
            <div className="flex flex-col items-center">
              <Upload className="w-12 h-12 text-gray-400 mb-4" />
              <p className="text-lg font-medium text-gray-900 mb-2">
                {isDragActive
                  ? isDragReject
                    ? 'File type not supported'
                    : 'Drop your document here'
                  : 'Drag and drop a document here'}
              </p>
              <p className="text-sm text-gray-500 mb-4">
                or click to browse files
              </p>
              <div className="flex items-center space-x-2 text-xs text-gray-400">
                <FileText className="w-4 h-4" />
                <span>Supports PDF, TXT, DOC, DOCX (max 50MB)</span>
              </div>
            </div>
          )}
        </div>

        {/* Status Messages */}
        {uploadStatus.status !== 'idle' && uploadStatus.status !== 'uploading' && (
          <div className="mt-6">
            {uploadStatus.status === 'success' && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start">
                  <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-green-800">
                      Upload Successful
                    </h3>
                    <p className="text-sm text-green-700 mt-1">{uploadStatus.message}</p>
                    {uploadStatus.response && (
                      <div className="mt-3 text-sm text-green-700 bg-white bg-opacity-50 rounded p-3">
                        <p><strong>Filename:</strong> {uploadStatus.response.filename}</p>
                        <p><strong>Document ID:</strong> {uploadStatus.response.document_id}</p>
                        <p><strong>Chunks Created:</strong> {uploadStatus.response.chunks_created}</p>
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={resetUpload}
                  className="mt-3 text-sm text-green-600 hover:text-green-500 font-medium"
                >
                  Upload Another Document
                </button>
              </div>
            )}

            {uploadStatus.status === 'error' && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-red-800">
                      Upload Failed
                    </h3>
                    <p className="text-sm text-red-700 mt-1">{uploadStatus.message}</p>
                  </div>
                </div>
                <button
                  onClick={resetUpload}
                  className="mt-3 text-sm text-red-600 hover:text-red-500 font-medium"
                >
                  Try Again
                </button>
              </div>
            )}
          </div>
        )}

        {/* Instructions */}
        <div className="mt-8 bg-gray-50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-2">Instructions:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>1. Upload a document (PDF, TXT, DOC, or DOCX)</li>
            <li>2. The system will process and chunk your document</li>
            <li>3. Go to the Chat tab to ask questions about the content</li>
            <li>4. The chatbot will answer based on the uploaded documents</li>
          </ul>
        </div>
      </div>
    </div>
  );
};