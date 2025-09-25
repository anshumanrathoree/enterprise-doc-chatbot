#!/usr/bin/env python3

import os
import sys
import subprocess
import time
from pathlib import Path

def check_ollama():
    """Check if Ollama is available"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def setup_environment():
    """Setup environment and check dependencies"""
    print("🚀 Starting Enterprise Document Chatbot Backend")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("main.py").exists():
        print("❌ Error: main.py not found. Please run this script from the backend directory.")
        sys.exit(1)

    # Check if .env exists
    if not Path(".env").exists():
        if Path(".env.example").exists():
            print("📋 Creating .env from .env.example...")
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file")
        else:
            print("⚠️  Warning: No .env file found")

    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("chroma_db", exist_ok=True)
    print("📁 Created necessary directories")

    # Check Ollama
    print("🔍 Checking Ollama installation...")
    if check_ollama():
        print("✅ Ollama is available")

        # Check if default model is available
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if 'llama2' not in result.stdout:
                print("📥 Default model 'llama2' not found. Pulling...")
                print("⏳ This may take a few minutes...")
                subprocess.run(['ollama', 'pull', 'llama2'])
                print("✅ Downloaded llama2 model")
            else:
                print("✅ Default model 'llama2' is available")
        except Exception as e:
            print(f"⚠️  Warning: Could not check models: {e}")
    else:
        print("❌ Ollama not found!")
        print("   Please install Ollama from: https://ollama.ai/")
        print("   Then run: ollama pull llama2")
        print("   And start: ollama serve")
        response = input("   Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)

    print("=" * 50)

def start_server():
    """Start the FastAPI server"""
    try:
        print("🌐 Starting FastAPI server on http://localhost:8000")
        print("📄 API documentation: http://localhost:8000/docs")
        print("🏥 Health check: http://localhost:8000/health")
        print("=" * 50)
        print("💡 Tips:")
        print("   - Upload documents at http://localhost:3000")
        print("   - Press Ctrl+C to stop the server")
        print("=" * 50)

        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])

    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_environment()
    start_server()