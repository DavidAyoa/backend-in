#!/usr/bin/env python3
"""
Simple test script for multi-agent conversation management
Tests basic functionality without external dependencies
"""

import asyncio
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import():
    """Test that we can import the session manager"""
    try:
        # Test importing our session manager
        from services.session_manager import AgentSessionManager, AgentSession
        print("✅ Successfully imported session manager components")
        return True
    except ImportError as e:
        print(f"❌ Failed to import session manager: {e}")
        return False

def test_basic_functionality():
    """Test basic session manager functionality"""
    try:
        from services.session_manager import AgentSessionManager
        
        # Create a session manager
        manager = AgentSessionManager()
        print("✅ Created session manager")
        
        # Create a few test sessions
        session1 = manager.create_session(
            agent_id=1,
            system_prompt="You are a helpful customer service representative."
        )
        print(f"✅ Created session 1: {session1}")
        
        session2 = manager.create_session(
            agent_id=2,
            system_prompt="You are a technical support specialist."
        )
        print(f"✅ Created session 2: {session2}")
        
        # Test session retrieval
        s1 = manager.get_session(session1)
        s2 = manager.get_session(session2)
        
        if s1 and s2:
            print("✅ Successfully retrieved sessions")
            print(f"   Session 1 - Agent ID: {s1.agent_id}, Messages: {len(s1.context.messages)}")
            print(f"   Session 2 - Agent ID: {s2.agent_id}, Messages: {len(s2.context.messages)}")
        else:
            print("❌ Failed to retrieve sessions")
            return False
        
        # Test adding messages to different sessions
        manager.add_user_message(session1, "Hello, I need help with my order")
        manager.add_assistant_message(session1, "I'd be happy to help you with your order!")
        
        manager.add_user_message(session2, "My computer won't start")
        manager.add_assistant_message(session2, "Let's troubleshoot this step by step...")
        
        # Check context isolation
        s1_updated = manager.get_session(session1)
        s2_updated = manager.get_session(session2)
        
        if s1_updated and s2_updated:
            print("✅ Messages added successfully")
            print(f"   Session 1 now has {len(s1_updated.context.messages)} messages")
            print(f"   Session 2 now has {len(s2_updated.context.messages)} messages")
            
            # Verify contexts are isolated
            if (len(s1_updated.context.messages) == 3 and  # system + user + assistant
                len(s2_updated.context.messages) == 3):
                print("✅ Context isolation working correctly")
            else:
                print("❌ Context isolation failed")
                return False
        
        # Test session listing
        all_sessions = manager.list_sessions()
        print(f"✅ Found {len(all_sessions)} total sessions")
        
        sessions_for_agent_1 = manager.list_sessions(agent_id=1)
        sessions_for_agent_2 = manager.list_sessions(agent_id=2)
        
        print(f"   Sessions for agent 1: {len(sessions_for_agent_1)}")
        print(f"   Sessions for agent 2: {len(sessions_for_agent_2)}")
        
        # Test session stats
        stats = manager.get_stats()
        print(f"✅ Session stats: {stats['total_sessions']} sessions")
        
        # Clean up
        manager.delete_session(session1)
        manager.delete_session(session2)
        print("✅ Cleaned up test sessions")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_configuration_check():
    """Test that configuration files exist"""
    try:
        import config
        print("✅ Configuration module imported successfully")
        
        # Check for required configuration attributes
        required_attrs = ['OPENAI_API_KEY', 'OPENAI_MODEL', 'OPENAI_TEMPERATURE', 'OPENAI_MAX_TOKENS']
        missing_attrs = []
        
        for attr in required_attrs:
            if not hasattr(config.config, attr):
                missing_attrs.append(attr)
        
        if missing_attrs:
            print(f"⚠️  Missing configuration attributes: {missing_attrs}")
            return False
        else:
            print("✅ All required configuration attributes found")
            return True
            
    except ImportError as e:
        print(f"❌ Configuration import failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    required_files = [
        'services/session_manager.py',
        'bot/fast_api.py',
        'main.py',
        'config.py',
        'routers/agents.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    else:
        print("✅ All required files exist")
        return True

def main():
    """Run all tests"""
    print("🚀 Starting Multi-Agent System Tests")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Import Test", test_import),
        ("Configuration Check", test_configuration_check),
        ("Basic Functionality", test_basic_functionality),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    success_rate = (passed / total) * 100
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Success Rate: {success_rate:.1f}%")
    
    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:20} {status}")
    
    if success_rate >= 100:
        print("\n🎉 EXCELLENT: All tests passed!")
    elif success_rate >= 75:
        print("\n✅ GOOD: Most tests passed")
    elif success_rate >= 50:
        print("\n⚠️  MODERATE: Some tests failed")
    else:
        print("\n❌ POOR: Many tests failed")
    
    print("\n" + "=" * 50)
    
    if success_rate >= 75:
        print("✅ Multi-agent conversation system is ready!")
        print("\nNext steps:")
        print("1. Start the server: python main.py")
        print("2. Create agents via API: POST /agents/")
        print("3. Connect WebSocket with agent: ws://localhost:8000/ws/auth?token=TOKEN&agent_id=1")
        print("4. Each connection maintains separate conversation context")
    else:
        print("❌ Multi-agent system needs attention before use")

if __name__ == "__main__":
    main()
