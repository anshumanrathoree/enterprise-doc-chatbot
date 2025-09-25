import React, { useState, useRef, useEffect } from 'react';
import { sendMessage, ChatMessage, DocumentChunk } from '../services/api';
import { Send, RefreshCw, Trash2, User, Bot, FileText } from 'lucide-react';

interface ChatInterfaceProps {
  conversationHistory: ChatMessage[];
  addToConversation: (message: ChatMessage) => void;
  clearConversation: () => void;
  onSourcesUpdate: (sources: DocumentChunk[]) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  conversationHistory,
  addToConversation,
  clearConversation,
  onSourcesUpdate
}) => {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: message };
    addToConversation(userMessage);
    setMessage('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage({
        message: message,
        conversation_history: conversationHistory
      });

      if (response.success) {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.response
        };
        addToConversation(assistantMessage);
        const responseSources = response.sources || [];
        onSourcesUpdate(responseSources);
      } else {
        setError('Failed to get response from the chatbot');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred while sending the message');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex justify-between items-center p-6 border-b bg-gradient-to-r from-blue-50 to-purple-50">
        <div>
          <h2 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            AI Document Assistant
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Ask questions about your uploaded documents
          </p>
        </div>
        <button
          onClick={clearConversation}
          className="flex items-center px-4 py-2 text-sm font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-gray-200 hover:border-red-200"
          disabled={conversationHistory.length === 0}
        >
          <Trash2 className="w-4 h-4 mr-2" />
          Clear Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/30">
        {conversationHistory.length === 0 ? (
          <div className="text-center text-gray-500 py-16">
            <div className="bg-gradient-to-r from-blue-100 to-purple-100 w-24 h-24 rounded-full mx-auto mb-6 flex items-center justify-center">
              <Bot className="w-12 h-12 text-purple-600" />
            </div>
            <h3 className="text-xl font-semibold mb-3 text-gray-700">Ready to assist you!</h3>
            <p className="text-gray-600 max-w-md mx-auto leading-relaxed">
              Upload some documents and start asking questions. I'll help you find answers using AI-powered document analysis.
            </p>
            <div className="mt-6 flex justify-center space-x-4">
              <div className="flex items-center text-sm text-gray-500">
                <FileText className="w-4 h-4 mr-1" />
                PDF, DOC, TXT supported
              </div>
              <div className="flex items-center text-sm text-gray-500">
                <Bot className="w-4 h-4 mr-1" />
                AI-powered responses
              </div>
            </div>
          </div>
        ) : (
          conversationHistory.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex items-start max-w-[75%] ${
                  msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                }`}
              >
                <div
                  className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white ml-3'
                      : 'bg-white text-purple-600 mr-3 border border-purple-100'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <User className="w-5 h-5" />
                  ) : (
                    <Bot className="w-5 h-5" />
                  )}
                </div>
                <div
                  className={`p-4 rounded-2xl shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
                      : 'bg-white text-gray-900 border border-gray-100'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-start">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white text-purple-600 mr-3 flex items-center justify-center shadow-sm border border-purple-100">
                <Bot className="w-5 h-5" />
              </div>
              <div className="bg-white text-gray-900 p-4 rounded-2xl shadow-sm border border-gray-100">
                <div className="flex items-center">
                  <RefreshCw className="w-4 h-4 animate-spin mr-2 text-purple-600" />
                  <span className="text-gray-700">AI is thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 shadow-sm">
            <p className="text-red-800 text-sm leading-relaxed">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>


      {/* Input Form */}
      <form onSubmit={handleSubmit} className="border-t bg-white p-6">
        <div className="flex space-x-4">
          <div className="flex-1 relative">
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="w-full border border-gray-300 rounded-xl px-6 py-4 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent shadow-sm transition-all"
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={!message.trim() || isLoading}
            className="bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-4 rounded-xl hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center shadow-sm transition-all font-medium"
          >
            {isLoading ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
            <span className="ml-2">Send</span>
          </button>
        </div>
      </form>
    </div>
  );
};