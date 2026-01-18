#!/bin/bash

echo "============================================"
echo "     AI Storyboard Pro v2.0"
echo "     AI Smart Storyboard System"
echo "============================================"
echo

cd "$(dirname "$0")"

# Check and kill process on port 7861
echo "[1/4] Checking port 7861..."
PID=$(lsof -t -i:7861 2>/dev/null)
if [ -n "$PID" ]; then
    echo "       Found process (PID: $PID)"
    echo "       Killing..."
    kill -9 $PID 2>/dev/null
fi
echo "       Port 7861 cleared"

echo
echo "[2/4] Checking dependencies..."
if ! pip show gradio >/dev/null 2>&1; then
    echo "       Installing dependencies..."
    pip install -r requirements.txt
else
    echo "       Dependencies OK"
fi

echo
echo "[3/4] Checking configuration..."
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
echo "[4/4] Starting server..."
echo
echo "============================================"
echo "   Server URL: http://localhost:7861"
echo "   Press Ctrl+C to stop"
echo "============================================"
echo

python app.py
