#!/usr/bin/env python3
"""
Test runner for Pipecat voice agent system
Provides various test execution options
"""

import sys
import subprocess
import argparse
import asyncio
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def install_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")
    return run_command([
        "uv", "pip", "install", "-r", "requirements-test.txt"
    ], "Installing test dependencies")

def run_unit_tests():
    """Run unit tests"""
    return run_command([
        "uv", "run", "pytest", 
        "test_flexible_conversation.py",
        "-v", "--tb=short"
    ], "Running unit tests")

def run_server_tests():
    """Run server endpoint tests"""
    return run_command([
        "uv", "run", "pytest", 
        "test_server_endpoints.py",
        "-v", "--tb=short"
    ], "Running server endpoint tests")

def run_all_tests():
    """Run all tests"""
    return run_command([
        "uv", "run", "pytest", 
        "test_flexible_conversation.py",
        "test_server_endpoints.py",
        "-v", "--tb=short"
    ], "Running all tests")

def run_tests_with_coverage():
    """Run tests with coverage report"""
    return run_command([
        "uv", "run", "pytest", 
        "test_flexible_conversation.py",
        "test_server_endpoints.py",
        "--cov=bot.flexible_conversation",
        "--cov=server",
        "--cov-report=term-missing",
        "--cov-report=html",
        "-v"
    ], "Running tests with coverage")

def run_integration_tests():
    """Run integration tests"""
    return run_command([
        "uv", "run", "pytest", 
        "-m", "integration",
        "-v", "--tb=short"
    ], "Running integration tests")

def run_performance_tests():
    """Run performance tests"""
    return run_command([
        "uv", "run", "pytest", 
        "-m", "slow",
        "-v", "--tb=short"
    ], "Running performance tests")

def run_legacy_api_tests():
    """Run legacy API tests (requires server running)"""
    print("🧪 Running legacy API tests (requires server)")
    
    # Check if server is running
    import httpx
    try:
        import httpx
        with httpx.Client() as client:
            response = client.get("http://localhost:7860/health", timeout=5.0)
            if response.status_code != 200:
                print("❌ Server is not responding properly")
                print("   Please start the server with: python3 main.py")
                return False
    except Exception as e:
        print("❌ Server is not running")
        print("   Please start the server with: python3 main.py")
        print(f"   Error: {e}")
        return False
    
    print("✅ Server is running, starting legacy API tests...\n")
    
    # Run legacy tests
    try:
        from tests.test_api_comprehensive import VoiceAgentAPITester
        
        async def run_legacy():
            async with VoiceAgentAPITester() as tester:
                results = await tester.run_all_tests()
                tester.print_test_summary(results)
                
                # Return success status
                passed = sum(1 for result in results.values() if result)
                total = len(results)
                success_rate = (passed / total) * 100
                
                return success_rate >= 80  # 80% success rate required
        
        return asyncio.run(run_legacy())
    except ImportError:
        print("❌ Legacy API tests not available")
        return False

def lint_code():
    """Run code linting"""
    success = True
    
    # Run flake8
    success &= run_command([
        sys.executable, "-m", "flake8", 
        "bot/flexible_conversation.py",
        "server.py",
        "test_flexible_conversation.py",
        "test_server_endpoints.py",
        "--max-line-length=100",
        "--ignore=E501,W503"
    ], "Running flake8 linting")
    
    return success

def format_code():
    """Format code with black"""
    return run_command([
        sys.executable, "-m", "black", 
        "bot/flexible_conversation.py",
        "server.py",
        "test_flexible_conversation.py",
        "test_server_endpoints.py"
    ], "Formatting code with black")

def run_specific_test(test_name):
    """Run a specific test"""
    return run_command([
        "uv", "run", "pytest", 
        f"-k", test_name,
        "-v", "--tb=short"
    ], f"Running test: {test_name}")

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Test runner for Pipecat voice agent system")
    parser.add_argument("--install", action="store_true", help="Install test dependencies")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--server", action="store_true", help="Run server tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--performance", action="store_true", help="Run performance tests")
    parser.add_argument("--legacy", action="store_true", help="Run legacy API tests")
    parser.add_argument("--lint", action="store_true", help="Run code linting")
    parser.add_argument("--format", action="store_true", help="Format code")
    parser.add_argument("--test", type=str, help="Run specific test by name")
    parser.add_argument("--ci", action="store_true", help="Run CI pipeline (all checks)")
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent
    import os
    os.chdir(script_dir)
    
    success = True
    
    if args.install:
        success &= install_dependencies()
    
    if args.unit:
        success &= run_unit_tests()
    
    if args.server:
        success &= run_server_tests()
    
    if args.all:
        success &= run_all_tests()
    
    if args.coverage:
        success &= run_tests_with_coverage()
    
    if args.integration:
        success &= run_integration_tests()
    
    if args.performance:
        success &= run_performance_tests()
    
    if args.legacy:
        success &= run_legacy_api_tests()
    
    if args.lint:
        success &= lint_code()
    
    if args.format:
        success &= format_code()
    
    if args.test:
        success &= run_specific_test(args.test)
    
    if args.ci:
        print("\n🚀 Running CI pipeline...")
        success &= install_dependencies()
        success &= lint_code()
        success &= run_tests_with_coverage()
        success &= run_integration_tests()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        print("\n📋 Quick start commands:")
        print("  python run_tests.py --install     # Install dependencies")
        print("  python run_tests.py --all         # Run all tests")
        print("  python run_tests.py --coverage    # Run tests with coverage")
        print("  python run_tests.py --legacy      # Run legacy API tests")
        print("  python run_tests.py --ci          # Run full CI pipeline")
        return
    
    if success:
        print("\n🎉 All operations completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Some operations failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
