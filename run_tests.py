#!/usr/bin/env python3
"""
Test Runner for Voice Agent Backend
Runs comprehensive API tests and provides detailed reporting
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.test_api_comprehensive import VoiceAgentAPITester

async def main():
    """Main test runner function"""
    print("🧪 Voice Agent Backend Test Runner")
    print("=" * 50)
    
    # Check if server is running
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:7860/health", timeout=5.0)
            if response.status_code != 200:
                print("❌ Server is not responding properly")
                print("   Please start the server with: python3 main.py")
                return False
    except Exception as e:
        print("❌ Server is not running")
        print("   Please start the server with: python3 main.py")
        print(f"   Error: {e}")
        return False
    
    print("✅ Server is running, starting tests...\n")
    
    # Run comprehensive tests
    async with VoiceAgentAPITester() as tester:
        results = await tester.run_all_tests()
        tester.print_test_summary(results)
        
        # Return success status
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        success_rate = (passed / total) * 100
        
        return success_rate >= 80  # 80% success rate required

if __name__ == "__main__":
    success = asyncio.run(main())
    exit_code = 0 if success else 1
    sys.exit(exit_code)
