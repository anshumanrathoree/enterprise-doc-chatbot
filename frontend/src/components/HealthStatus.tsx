import React, { useState, useEffect } from 'react';
import { checkHealth, HealthResponse } from '../services/api';
import { CheckCircle, XCircle, RefreshCw, Activity, Server, Database } from 'lucide-react';

export const HealthStatus: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);

  const checkSystemHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await checkHealth();
      setHealth(response);
      setLastCheck(new Date());
    } catch (err: any) {
      setError(err.message || 'Failed to check system health');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkSystemHealth();

    // Auto-refresh every 30 seconds
    const interval = setInterval(checkSystemHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'connected':
      case 'initialized':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'unhealthy':
      case 'disconnected':
        return <XCircle className="w-5 h-5 text-red-600" />;
      default:
        return <RefreshCw className="w-5 h-5 text-yellow-600 animate-spin" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'connected':
      case 'initialized':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'unhealthy':
      case 'disconnected':
        return 'bg-red-50 border-red-200 text-red-800';
      default:
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
    }
  };

  const overallStatus = health?.status === 'healthy' ? 'healthy' : 'unhealthy';

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">System Health</h2>
          <button
            onClick={checkSystemHealth}
            disabled={loading}
            className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Overall Status */}
        <div className={`rounded-lg p-4 mb-6 border ${getStatusColor(overallStatus)}`}>
          <div className="flex items-center">
            {getStatusIcon(overallStatus)}
            <div className="ml-3">
              <h3 className="text-lg font-medium">
                System Status: {overallStatus === 'healthy' ? 'Healthy' : 'Issues Detected'}
              </h3>
              {lastCheck && (
                <p className="text-sm opacity-75">
                  Last checked: {lastCheck.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
        </div>

        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <XCircle className="w-5 h-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
              <div>
                <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
                <p className="text-sm text-red-600 mt-2">
                  Make sure the backend server is running on port 8000.
                </p>
              </div>
            </div>
          </div>
        ) : health ? (
          <div className="space-y-4">
            {/* API Server Status */}
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Server className="w-6 h-6 text-gray-400 mr-3" />
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">API Server</h3>
                    <p className="text-sm text-gray-600">FastAPI backend service</p>
                  </div>
                </div>
                <div className="flex items-center">
                  {getStatusIcon(health.status)}
                  <span className="ml-2 text-sm font-medium capitalize">
                    {health.status}
                  </span>
                </div>
              </div>
            </div>

            {/* Ollama Service Status */}
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Activity className="w-6 h-6 text-gray-400 mr-3" />
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">Ollama Service</h3>
                    <p className="text-sm text-gray-600">Local AI model service</p>
                  </div>
                </div>
                <div className="flex items-center">
                  {getStatusIcon(health.ollama_service)}
                  <span className="ml-2 text-sm font-medium capitalize">
                    {health.ollama_service}
                  </span>
                </div>
              </div>
              {health.ollama_service === 'disconnected' && (
                <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-sm text-yellow-800">
                    Ollama service is not available. Please ensure Ollama is installed and running.
                  </p>
                  <p className="text-sm text-yellow-700 mt-1">
                    Run: <code className="bg-yellow-100 px-1 rounded">ollama serve</code>
                  </p>
                </div>
              )}
            </div>

            {/* Vector Store Status */}
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <Database className="w-6 h-6 text-gray-400 mr-3" />
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">Vector Database</h3>
                    <p className="text-sm text-gray-600">ChromaDB for document embeddings</p>
                  </div>
                </div>
                <div className="flex items-center">
                  {getStatusIcon(health.vector_store)}
                  <span className="ml-2 text-sm font-medium capitalize">
                    {health.vector_store}
                  </span>
                </div>
              </div>
            </div>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin mr-3" />
            <span className="text-gray-600">Checking system health...</span>
          </div>
        ) : null}

        {/* System Information */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-4">System Information</h3>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Backend URL:</span>
                <span className="ml-2 font-mono text-gray-900">
                  {process.env.REACT_APP_API_URL || 'http://localhost:8000'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Frontend Version:</span>
                <span className="ml-2 text-gray-900">1.0.0</span>
              </div>
              <div>
                <span className="text-gray-500">Environment:</span>
                <span className="ml-2 text-gray-900">
                  {process.env.NODE_ENV || 'development'}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Auto-refresh:</span>
                <span className="ml-2 text-gray-900">Every 30 seconds</span>
              </div>
            </div>
          </div>
        </div>

        {/* Troubleshooting */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Troubleshooting</h3>
          <div className="space-y-3 text-sm text-gray-600">
            <div>
              <strong>Backend not responding:</strong> Make sure the Python backend is running with{' '}
              <code className="bg-gray-100 px-1 rounded">python main.py</code>
            </div>
            <div>
              <strong>Ollama disconnected:</strong> Install and start Ollama with{' '}
              <code className="bg-gray-100 px-1 rounded">ollama serve</code>
            </div>
            <div>
              <strong>Missing models:</strong> Pull required models with{' '}
              <code className="bg-gray-100 px-1 rounded">ollama pull llama2</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};