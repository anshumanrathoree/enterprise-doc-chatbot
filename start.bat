@echo off
echo ===============================================
echo Enterprise Document Chatbot - Ollama Edition
echo ===============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found! Please install Node.js 16+
    pause
    exit /b 1
)

REM Check if Ollama is available
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Ollama not found! Please install from https://ollama.ai/
    echo Then run: ollama pull llama2
    pause
    exit /b 1
)

echo ✅ All prerequisites found!
echo.

REM Start Ollama serve if not running
echo 🔍 Checking Ollama service...
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo 🚀 Starting Ollama service...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
)

echo 🔍 Installing backend dependencies...
cd backend
if not exist ".env" (
    copy .env.example .env
    echo ✅ Created .env file
)

pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo ❌ Failed to install backend dependencies
    pause
    exit /b 1
)

echo 🔍 Installing frontend dependencies...
cd ..\frontend
call npm install >nul 2>&1
if errorlevel 1 (
    echo ❌ Failed to install frontend dependencies
    pause
    exit /b 1
)

echo.
echo 🚀 Starting servers...
echo 📄 Backend: http://localhost:8000
echo 🌐 Frontend: http://localhost:3000
echo.
echo Press Ctrl+C to stop all servers
echo.

REM Start backend in background
cd ..\backend
start "Backend Server" python start_backend.py

REM Wait a bit for backend to start
timeout /t 5 /nobreak >nul

REM Start frontend (this will be the main window)
cd ..\frontend
call npm start

echo.
echo 🛑 Servers stopped
pause