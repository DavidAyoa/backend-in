#!/bin/bash

# Voice Agent Backend - Server Startup Script

set -e

log() {
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

log "🚀 Starting Voice Agent Backend..."

# Check if uv is available
if ! command -v uv &> /dev/null; then
    log "❌ uv is not installed. Please install uv first."
    exit 1
fi

# Kill any existing server processes
log "🔄 Stopping any existing server processes..."
pkill -f "python main.py" 2> /dev/null || true
sleep 2

# Start the server in the background
log "🌟 Starting server..."
uv run python main.py &
SERVER_PID=$!

# Wait for the server to start
log "⏳ Waiting 15 seconds for server to initialize..."
sleep 15

# Test if the server is running
log "🔍 Testing server connection..."
log "Checking if process is still running..."
if ps -p $SERVER_PID > /dev/null; then
    log "✓ Server process is running (PID: $SERVER_PID)"
else
    log "❌ Server process has died"
fi

log "Testing HTTP connection..."
if curl -s http://localhost:7860/health > /dev/null; then
    log "✅ Server is running successfully!"
    log "🌐 Server URL: http://localhost:7860"
else
    log "❌ Server failed to start or is not responding"
    kill $SERVER_PID 2> /dev/null || true
    exit 1
fi
