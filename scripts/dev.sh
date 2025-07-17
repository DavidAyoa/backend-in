#!/bin/bash

# Development script for voice agent backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command_exists uv; then
        log_error "uv is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists docker; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists docker-compose; then
        log_error "Docker Compose is not installed. Please install it first."
        exit 1
    fi
    
    log_info "Dependencies check passed"
}

# Setup environment
setup_env() {
    log_info "Setting up environment..."
    
    # Copy environment template if .env doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.template .env
        log_warn "Created .env file from template. Please update it with your API keys."
    fi
    
    # Create .env.dev if it doesn't exist
    if [ ! -f ".env.dev" ]; then
        cp .env.template .env.dev
        echo "DEVELOPMENT=true" >> .env.dev
        log_info "Created .env.dev file"
    fi
    
    # Create .env.test if it doesn't exist
    if [ ! -f ".env.test" ]; then
        cp .env.template .env.test
        echo "TESTING=true" >> .env.test
        log_info "Created .env.test file"
    fi
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    uv sync --extra dev --extra test
    log_info "Dependencies installed"
}

# Start services
start_services() {
    log_info "Starting optional services..."
    
    # Create data directory for SQLite
    mkdir -p data logs
    
    # For now, we only use SQLite, but services can be started with profiles
    log_info "SQLite database will be created automatically"
    log_info "Optional services (redis/postgres) can be started with:"
    log_info "  docker-compose --profile redis up -d redis"
    log_info "  docker-compose --profile postgres up -d postgres"
}

# Stop services
stop_services() {
    log_info "Stopping services..."
    docker-compose down
    log_info "Services stopped"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    # Ensure services are running
    if ! docker-compose ps | grep -q "Up"; then
        log_info "Starting services for tests..."
        start_services
    fi
    
    # Run tests with coverage
    uv run pytest -v --cov=. --cov-report=html --cov-report=term
    
    log_info "Tests completed. Coverage report available in htmlcov/"
}

# Run linting
run_lint() {
    log_info "Running linting..."
    
    # Black formatting
    uv run black --check .
    
    # isort import sorting
    uv run isort --check-only .
    
    # flake8 linting
    uv run flake8 .
    
    # mypy type checking
    uv run mypy .
    
    log_info "Linting completed"
}

# Fix formatting
fix_format() {
    log_info "Fixing formatting..."
    
    # Black formatting
    uv run black .
    
    # isort import sorting
    uv run isort .
    
    log_info "Formatting fixed"
}

# Start development server
start_dev() {
    log_info "Starting development server..."
    
    # Start services
    start_services
    
    # Start development server
    uv run python -m main --reload
}

# Start with Docker Compose
start_docker() {
    log_info "Starting with Docker Compose..."
    docker-compose --profile dev up --build
}

# Clean up
cleanup() {
    log_info "Cleaning up..."
    
    # Remove cache files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove test artifacts
    rm -rf .pytest_cache htmlcov .coverage test-results
    
    # Remove build artifacts
    rm -rf dist build *.egg-info
    
    log_info "Cleanup completed"
}

# Show help
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup       Setup development environment"
    echo "  install     Install dependencies"
    echo "  start       Start development server"
    echo "  docker      Start with Docker Compose"
    echo "  test        Run tests"
    echo "  lint        Run linting"
    echo "  format      Fix formatting"
    echo "  services    Start background services"
    echo "  stop        Stop all services"
    echo "  clean       Clean up cache and artifacts"
    echo "  help        Show this help message"
}

# Main script
case "$1" in
    setup)
        check_dependencies
        setup_env
        install_deps
        ;;
    install)
        install_deps
        ;;
    start)
        start_dev
        ;;
    docker)
        start_docker
        ;;
    test)
        run_tests
        ;;
    lint)
        run_lint
        ;;
    format)
        fix_format
        ;;
    services)
        start_services
        ;;
    stop)
        stop_services
        ;;
    clean)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        log_info "Voice Agent Backend Development Script"
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
