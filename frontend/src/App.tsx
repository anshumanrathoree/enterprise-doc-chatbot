import React, { useState } from 'react';
import { DocumentUpload } from './components/DocumentUpload';
import { ChatInterface } from './components/ChatInterface';
import { DocumentList } from './components/DocumentList';
import { HealthStatus } from './components/HealthStatus';
import { ChatMessage, DocumentChunk } from './services/api';
import { FileText, MessageCircle, Database, Activity, Sparkles } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload' | 'documents' | 'health'>('chat');
  const [conversationHistory, setConversationHistory] = useState<ChatMessage[]>([]);
  const [currentSources, setCurrentSources] = useState<DocumentChunk[]>([]);

  const addToConversation = (message: ChatMessage) => {
    setConversationHistory(prev => [...prev, message]);
  };

  const clearConversation = () => {
    setConversationHistory([]);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <FileText className="w-8 h-8 text-primary-600 mr-3" />
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Enterprise Document Chatbot
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center text-sm text-purple-600 font-medium">
                <Sparkles className="w-4 h-4 mr-1" />
                Powered by Onira
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center px-3 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'chat'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <MessageCircle className="w-4 h-4 mr-2" />
              Chat
            </button>

            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center px-3 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'upload'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <FileText className="w-4 h-4 mr-2" />
              Upload Documents
            </button>

            <button
              onClick={() => setActiveTab('documents')}
              className={`flex items-center px-3 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'documents'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Database className="w-4 h-4 mr-2" />
              Manage Documents
            </button>

            <button
              onClick={() => setActiveTab('health')}
              className={`flex items-center px-3 py-4 text-sm font-medium border-b-2 ${
                activeTab === 'health'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Activity className="w-4 h-4 mr-2" />
              System Health
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="h-[calc(100vh-140px)]">
        {activeTab === 'chat' && (
          <div className="flex h-full">
            {/* Main Chat Area */}
            <div className="flex-1">
              <ChatInterface
                conversationHistory={conversationHistory}
                addToConversation={addToConversation}
                clearConversation={clearConversation}
                onSourcesUpdate={setCurrentSources}
              />
            </div>

            {/* Sources Sidebar */}
            <div className="w-96 border-l bg-gray-50">
              <div className="h-full flex flex-col">
                <div className="p-4 border-b bg-white">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                    <FileText className="w-5 h-5 mr-2 text-purple-600" />
                    Document Sources
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Relevant document sections
                  </p>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                  {currentSources.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p className="font-medium mb-2">No sources yet</p>
                      <p className="text-sm">
                        Ask a question to see relevant document sections here.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {currentSources.map((source, index) => (
                        <div
                          key={index}
                          className="bg-white p-4 rounded-lg shadow-sm border hover:shadow-md transition-shadow"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="font-medium text-gray-900 text-sm">
                              {source.metadata.filename}
                            </div>
                            {source.similarity_score && (
                              <div className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
                                {Math.abs(source.similarity_score * 100).toFixed(0)}% match
                              </div>
                            )}
                          </div>
                          <p className="text-gray-700 text-sm leading-relaxed">
                            {source.content.substring(0, 300)}
                            {source.content.length > 300 && '...'}
                          </p>
                          <div className="mt-2 text-xs text-gray-500">
                            Chunk {source.metadata.chunk_index + 1} • {source.metadata.file_type}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <DocumentUpload />
          </div>
        )}

        {activeTab === 'documents' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <DocumentList />
          </div>
        )}

        {activeTab === 'health' && (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <HealthStatus />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
