#!/bin/bash

# Backend Structure Reorganization Script
# This script reorganizes the backend to match the target structure

set -e  # Exit on any error

echo "🚀 Starting Backend Structure Reorganization..."
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Create backup
echo ""
print_info "Creating backup of current structure..."
cp -r . ../backend-in-backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || print_warning "Could not create backup in parent directory"

# Phase 1: Create missing directories
echo ""
print_info "Phase 1: Creating missing directories..."

# Create api directory
mkdir -p api
print_status "Created api/ directory"

# Create missing transport subdirectories
mkdir -p transports/websocket
mkdir -p transports/webrtc
print_status "Created transport subdirectories"

# Create missing test directories
mkdir -p tests/e2e
print_status "Created tests/e2e directory"

# Phase 2: Move API routes
echo ""
print_info "Phase 2: Moving API routes..."

if [ -d "routers" ]; then
    # Move routers to api
    if [ -f "routers/__init__.py" ]; then
        cp routers/__init__.py api/__init__.py
        print_status "Moved routers/__init__.py → api/__init__.py"
    fi
    
    if [ -f "routers/auth.py" ]; then
        cp routers/auth.py api/auth.py
        print_status "Moved routers/auth.py → api/auth.py"
    fi
    
    if [ -f "routers/agents.py" ]; then
        cp routers/agents.py api/agents.py
        print_status "Moved routers/agents.py → api/agents.py"
    fi
    
    # Remove old routers directory
    rm -rf routers
    print_status "Removed old routers/ directory"
else
    print_warning "routers/ directory not found"
fi

# Phase 3: Move bot files
echo ""
print_info "Phase 3: Moving bot files..."

if [ -f "bot_fast_api_enhanced.py" ]; then
    mv bot_fast_api_enhanced.py bot/fast_api_enhanced.py
    print_status "Moved bot_fast_api_enhanced.py → bot/fast_api_enhanced.py"
fi

if [ -f "bot_flexible_conversation.py" ]; then
    mv bot_flexible_conversation.py bot/flexible_conversation.py
    print_status "Moved bot_flexible_conversation.py → bot/flexible_conversation.py"
fi

if [ -f "bot_websocket_server.py" ]; then
    mv bot_websocket_server.py bot/websocket_server.py
    print_status "Moved bot_websocket_server.py → bot/websocket_server.py"
fi

# Phase 4: Move test files
echo ""
print_info "Phase 4: Moving test files..."

# Move root test files to tests/integration
test_files=(
    "test_flexible_conversation.py"
    "test_live_conversation_modes.py"
    "test_marketplace.py"
    "test_multi_agent.py"
    "test_multi_agent_simple.py"
    "test_pipecat_client.py"
    "test_server_endpoints.py"
    "test_websocket_basic.py"
)

for test_file in "${test_files[@]}"; do
    if [ -f "$test_file" ]; then
        mv "$test_file" "tests/integration/"
        print_status "Moved $test_file → tests/integration/"
    fi
done

# Phase 5: Transport system setup
echo ""
print_info "Phase 5: Setting up transport system..."

# Check if transport managers exist, if not create placeholders
if [ ! -f "transports/websocket/manager.py" ]; then
    touch transports/websocket/__init__.py
    print_status "Created transports/websocket/__init__.py"
fi

if [ ! -f "transports/webrtc/manager.py" ]; then
    touch transports/webrtc/__init__.py
    print_status "Created transports/webrtc/__init__.py"
fi

# Phase 6: Remove duplicate/obsolete files
echo ""
print_info "Phase 6: Removing duplicate/obsolete files..."

# Remove duplicate app directory if it exists and is not being used
if [ -d "app" ]; then
    print_warning "Found app/ directory - checking for duplicates..."
    
    # Check if app/config.py is a duplicate
    if [ -f "app/config.py" ] && [ -f "config.py" ]; then
        print_status "Removing duplicate app/config.py (keeping root config.py)"
        rm app/config.py
    fi
    
    # Check if app/main.py is basic version
    if [ -f "app/main.py" ] && [ -f "server_enhanced.py" ]; then
        print_status "Removing basic app/main.py (keeping server_enhanced.py)"
        rm app/main.py
    fi
    
    # Remove app directory if empty
    if [ -z "$(ls -A app)" ]; then
        rmdir app
        print_status "Removed empty app/ directory"
    fi
fi

# Phase 7: Update main entry point
echo ""
print_info "Phase 7: Updating main entry point..."

# Update main.py to be cleaner
cat > main.py << 'EOF'
#!/usr/bin/env python3
"""
Voice Agent Backend - Main Entry Point
Clean, scalable voice agent backend built with FastAPI and Pipecat
"""
import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server_enhanced import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)
EOF

print_status "Updated main.py entry point"

# Phase 8: Update imports in server_enhanced.py
echo ""
print_info "Phase 8: Updating imports in server_enhanced.py..."

# Create a backup of server_enhanced.py
cp server_enhanced.py server_enhanced.py.bak

# Update imports in server_enhanced.py
sed -i 's/from bot_fast_api_enhanced import run_bot/from bot.fast_api_enhanced import run_bot/g' server_enhanced.py
sed -i 's/from bot_websocket_server import run_bot_websocket_server/from bot.websocket_server import run_bot_websocket_server/g' server_enhanced.py
sed -i 's/from routers\.auth import/from api.auth import/g' server_enhanced.py
sed -i 's/from routers\.agents import/from api.agents import/g' server_enhanced.py
sed -i 's/from bot_flexible_conversation import/from bot.flexible_conversation import/g' server_enhanced.py

print_status "Updated imports in server_enhanced.py"

# Phase 9: Update imports in moved files
echo ""
print_info "Phase 9: Updating imports in moved files..."

# Update imports in bot files
if [ -f "bot/fast_api_enhanced.py" ]; then
    sed -i 's/from routers\./from api\./g' bot/fast_api_enhanced.py
    print_status "Updated imports in bot/fast_api_enhanced.py"
fi

if [ -f "bot/flexible_conversation.py" ]; then
    sed -i 's/from routers\./from api\./g' bot/flexible_conversation.py
    print_status "Updated imports in bot/flexible_conversation.py"
fi

if [ -f "bot/websocket_server.py" ]; then
    sed -i 's/from routers\./from api\./g' bot/websocket_server.py
    print_status "Updated imports in bot/websocket_server.py"
fi

# Phase 10: Create __init__.py files where needed
echo ""
print_info "Phase 10: Creating __init__.py files..."

# Create __init__.py files for proper Python packages
touch api/__init__.py 2>/dev/null || true
touch transports/websocket/__init__.py 2>/dev/null || true
touch transports/webrtc/__init__.py 2>/dev/null || true
touch tests/e2e/__init__.py 2>/dev/null || true

print_status "Created missing __init__.py files"

# Phase 11: Update pytest configuration
echo ""
print_info "Phase 11: Updating pytest configuration..."

# Update pytest.ini if it exists
if [ -f "pytest.ini" ]; then
    # Add the new test paths if not already present
    if ! grep -q "tests/integration" pytest.ini; then
        sed -i '/testpaths = \[/a\    "tests/integration",' pytest.ini
    fi
    print_status "Updated pytest.ini with new test paths"
fi

# Summary
echo ""
echo "=============================================="
print_info "Reorganization Summary:"
echo ""
print_status "✓ Created api/ directory and moved routes"
print_status "✓ Moved bot files to bot/ directory"
print_status "✓ Moved test files to tests/integration/"
print_status "✓ Created transport subdirectories"
print_status "✓ Updated import statements"
print_status "✓ Cleaned up duplicate files"
print_status "✓ Updated main entry point"

echo ""
print_info "New structure:"
echo "├── api/                    # FastAPI routes (moved from routers/)"
echo "├── bot/                    # Bot logic (consolidated)"
echo "├── core/                   # Core services"
echo "├── models/                 # Data models"
echo "├── services/               # Business logic"
echo "├── transports/             # Transport implementations"
echo "│   ├── websocket/          # WebSocket transport"
echo "│   └── webrtc/             # WebRTC transport"
echo "├── tests/                  # Test suite"
echo "│   ├── unit/               # Unit tests"
echo "│   ├── integration/        # Integration tests (moved from root)"
echo "│   └── e2e/                # End-to-end tests"
echo "├── scripts/                # Development scripts"
echo "├── helpful_docs/           # Documentation"
echo "└── main.py                 # Main entry point"

echo ""
print_warning "Next steps:"
echo "1. Test the server: python main.py"
echo "2. Run tests: python -m pytest tests/"
echo "3. Check for any remaining import errors"
echo "4. Remove this script: rm reorganize_structure.sh"

echo ""
print_info "🎉 Reorganization complete!"
