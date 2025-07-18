#!/usr/bin/env python3
"""
Test script for multi-agent conversation management
Tests the session manager and agent-specific contexts
"""

import asyncio
import json
import requests
from services.session_manager import session_manager

def test_session_manager():
    """Test the session manager functionality"""
    print("Testing Session Manager...")
    
    # Test creating sessions with different agents
    session1_id = session_manager.create_session(
        agent_id=1,
        system_prompt="You are a helpful customer service representative."
    )
    print(f"Created session 1: {session1_id}")
    
    session2_id = session_manager.create_session(
        agent_id=2,
        system_prompt="You are a technical support specialist."
    )
    print(f"Created session 2: {session2_id}")
    
    session3_id = session_manager.create_session(
        agent_id=3,
        system_prompt="You are a sales representative."
    )
    print(f"Created session 3: {session3_id}")
    
    # Test getting sessions
    session1 = session_manager.get_session(session1_id)
    session2 = session_manager.get_session(session2_id)
    session3 = session_manager.get_session(session3_id)
    
    print(f"Session 1 context: {len(session1.context.messages)} messages")
    print(f"Session 2 context: {len(session2.context.messages)} messages")
    print(f"Session 3 context: {len(session3.context.messages)} messages")
    
    # Test adding messages to different sessions
    session_manager.add_user_message(session1_id, "Hello, I need help with my order")
    session_manager.add_assistant_message(session1_id, "I'd be happy to help you with your order!")
    
    session_manager.add_user_message(session2_id, "My computer won't start")
    session_manager.add_assistant_message(session2_id, "Let's troubleshoot this step by step...")
    
    session_manager.add_user_message(session3_id, "I'm looking for a new laptop")
    session_manager.add_assistant_message(session3_id, "Great! I can help you find the perfect laptop...")
    
    # Verify context isolation
    print(f"\nAfter adding messages:")
    print(f"Session 1 context: {len(session1.context.messages)} messages")
    print(f"Session 2 context: {len(session2.context.messages)} messages") 
    print(f"Session 3 context: {len(session3.context.messages)} messages")
    
    # Test listing sessions
    all_sessions = session_manager.list_sessions()
    print(f"\nTotal sessions: {len(all_sessions)}")
    
    sessions_for_agent_1 = session_manager.list_sessions(agent_id=1)
    print(f"Sessions for agent 1: {len(sessions_for_agent_1)}")
    
    # Test session stats
    stats = session_manager.get_stats()
    print(f"\nSession manager stats: {stats}")
    
    # Clean up
    session_manager.delete_session(session1_id)
    session_manager.delete_session(session2_id)
    session_manager.delete_session(session3_id)
    
    print("Session manager test completed!")

def test_api_endpoints():
    """Test the API endpoints (if server is running)"""
    print("\nTesting API endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        # Test health check
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✓ Health check passed")
        else:
            print("✗ Health check failed")
        
        # Test session manager stats
        response = requests.get(f"{base_url}/session-manager/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Session manager stats: {stats}")
        else:
            print("✗ Session manager stats failed")
            
    except requests.exceptions.ConnectionError:
        print("Server not running - skipping API tests")

def example_usage():
    """Show example usage of the multi-agent system"""
    print("\n" + "="*50)
    print("EXAMPLE USAGE")
    print("="*50)
    
    print("""
1. Create agents with different system prompts via API:
   POST /agents/
   {
     "agent_name": "Customer Support",
     "system_prompt": "You are a helpful customer service representative.",
     "description": "Handles customer inquiries and support requests"
   }

2. Connect to WebSocket with specific agent:
   ws://localhost:8000/ws/auth?token=YOUR_TOKEN&agent_id=1

3. Each WebSocket connection will use the agent's system prompt
   and maintain isolated conversation context.

4. Multiple connections to the same agent will have separate contexts.

5. Monitor sessions via API:
   GET /session-manager/sessions
   GET /session-manager/stats

6. Clean up inactive sessions:
   POST /session-manager/cleanup
   """)

if __name__ == "__main__":
    test_session_manager()
    test_api_endpoints()
    example_usage()
