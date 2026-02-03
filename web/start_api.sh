#!/bin/bash

echo "============================================"
echo " AI Storyboard Pro API Server"
echo "============================================"
echo

cd "$(dirname "$0")"

# Kill existing processes on port 8000
echo "[1/3] Checking port 8000..."
PID=$(lsof -t -i:8000 2>/dev/null)
if [ -n "$PID" ]; then
    echo "       Killing process (PID: $PID)"
    kill -9 $PID 2>/dev/null
fi
echo "       Port cleared"

echo
echo "[2/3] Checking configuration..."
if [ ! -f ".env" ]; then
    echo "       No configuration found."
    echo "       Running setup wizard..."
    echo
    python setup_wizard.py
    if [ $? -ne 0 ]; then
        echo
        echo "       Setup failed or cancelled."
        echo "       Please create .env from .env.example"
        exit 1
    fi
else
    echo "       Configuration OK"
fi

echo
echo "[3/3] Starting API Server..."
echo
echo "============================================"
echo "   API Docs: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo "   Press Ctrl+C to stop"
echo "============================================"
echo

python api_server.py
