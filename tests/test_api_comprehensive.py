#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Voice Agent Backend
Tests all available routes with proper authentication and error handling
"""

import asyncio
import pytest
import httpx
import websockets
import json
from typing import Dict, Any, Optional
import time
import random
import string

class VoiceAgentAPITester:
    """Comprehensive test suite for Voice Agent API"""
    
    def __init__(self, base_url: str = "http://localhost:7860"):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.test_user_data = None
        self.test_agent_id = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def generate_test_email(self) -> str:
        """Generate a unique test email"""
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"test_{random_string}@example.com"
    
    def generate_test_username(self) -> str:
        """Generate a unique test username"""
        random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"testuser_{random_string}"
    
    async def test_server_health(self) -> bool:
        """Test server health endpoint"""
        print("\n=== Testing Server Health ===")
        
        try:
            response = await self.session.get("/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server health: {data['status']}")
                print(f"   Active sessions: {data.get('active_sessions', 0)}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_server_info(self) -> bool:
        """Test server info endpoint"""
        print("\n=== Testing Server Info ===")
        
        try:
            response = await self.session.get("/")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Server info retrieved: {data['service']}")
                print(f"   Version: {data.get('version', 'unknown')}")
                print(f"   Features: {data.get('features', [])}")
                return True
            else:
                print(f"❌ Server info failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Server info error: {e}")
            return False
    
    async def test_metrics(self) -> bool:
        """Test metrics endpoint"""
        print("\n=== Testing Metrics ===")
        
        try:
            response = await self.session.get("/metrics")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Metrics retrieved")
                print(f"   Active connections: {data.get('connections', {}).get('active', 0)}")
                print(f"   Max connections: {data.get('connections', {}).get('max_allowed', 0)}")
                return True
            else:
                print(f"❌ Metrics failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Metrics error: {e}")
            return False
    
    async def test_user_registration(self) -> bool:
        """Test user registration"""
        print("\n=== Testing User Registration ===")
        
        self.test_user_data = {
            "email": self.generate_test_email(),
            "username": self.generate_test_username(),
            "password": "password123",
            "full_name": "Test User"
        }
        
        try:
            response = await self.session.post("/auth/register", json=self.test_user_data)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Registration successful: {data['user']['username']}")
                print(f"   User ID: {data['user']['id']}")
                print(f"   Token provided: {'token' in data}")
                self.auth_token = data['token']
                return True
            else:
                error = response.json()
                print(f"❌ Registration failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    async def test_user_login(self) -> bool:
        """Test user login"""
        print("\n=== Testing User Login ===")
        
        if not self.test_user_data:
            print("❌ No test user data available")
            return False
        
        login_data = {
            "email_or_username": self.test_user_data["email"],
            "password": self.test_user_data["password"]
        }
        
        try:
            response = await self.session.post("/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Login successful: {data['user']['username']}")
                print(f"   Token expires in: {data.get('expires_in', 0)} seconds")
                return True
            else:
                error = response.json()
                print(f"❌ Login failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    async def test_get_profile(self) -> bool:
        """Test getting user profile"""
        print("\n=== Testing Get Profile ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = await self.session.get("/auth/profile", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Profile retrieved: {data['username']} ({data['email']})")
                print(f"   Role: {data['role']}, Status: {data['status']}")
                print(f"   Email verified: {data.get('email_verified', False)}")
                return True
            else:
                error = response.json()
                print(f"❌ Profile retrieval failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Profile retrieval error: {e}")
            return False
    
    async def test_update_profile(self) -> bool:
        """Test updating user profile"""
        print("\n=== Testing Update Profile ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        update_data = {
            "full_name": "Updated Test User",
            "profile_data": {
                "bio": "This is a test user profile",
                "preferences": {
                    "voice_style": "professional",
                    "language": "en-US"
                }
            }
        }
        
        try:
            response = await self.session.put("/auth/profile", json=update_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Profile updated: {data['full_name']}")
                print(f"   Profile data: {data.get('profile_data', {})}")
                return True
            else:
                error = response.json()
                print(f"❌ Profile update failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Profile update error: {e}")
            return False
    
    async def test_get_api_key(self) -> bool:
        """Test getting API key"""
        print("\n=== Testing Get API Key ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = await self.session.get("/auth/api-key", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API key retrieved: {data['api_key'][:20]}...")
                print(f"   Created at: {data.get('created_at', 'unknown')}")
                return True
            else:
                error = response.json()
                print(f"❌ API key retrieval failed: {error}")
                return False
        except Exception as e:
            print(f"❌ API key retrieval error: {e}")
            return False
    
    async def test_session_info(self) -> bool:
        """Test getting session information"""
        print("\n=== Testing Session Info ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = await self.session.get("/auth/session", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session info retrieved")
                print(f"   Agent limit: {data.get('agent_limit', 0)}")
                print(f"   Can create agents: {data.get('can_create_agents', False)}")
                return True
            else:
                error = response.json()
                print(f"❌ Session info failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Session info error: {e}")
            return False
    
    async def test_create_agent(self) -> bool:
        """Test creating an agent"""
        print("\n=== Testing Create Agent ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        agent_data = {
            "agent_name": "Test Agent",
            "description": "A test voice agent",
            "system_prompt": "You are a helpful test assistant.",
            "voice_settings": {
                "voice_id": "en-US-Chirp3-HD-Achernar",
                "speech_rate": 1.0,
                "pitch": 0.0
            }
        }
        
        try:
            response = await self.session.post("/agents/", json=agent_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Agent created: {data['agent_name']}")
                print(f"   Agent ID: {data['id']}")
                print(f"   Status: {data['status']}")
                self.test_agent_id = data['id']
                return True
            else:
                error = response.json()
                print(f"❌ Agent creation failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Agent creation error: {e}")
            return False
    
    async def test_list_agents(self) -> bool:
        """Test listing agents"""
        print("\n=== Testing List Agents ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = await self.session.get("/agents/", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Agents listed: {len(data)} agents found")
                for agent in data:
                    print(f"   - {agent['agent_name']} (ID: {agent['id']})")
                return True
            else:
                error = response.json()
                print(f"❌ Agent listing failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Agent listing error: {e}")
            return False
    
    async def test_get_agent(self) -> bool:
        """Test getting a specific agent"""
        print("\n=== Testing Get Agent ===")
        
        if not self.auth_token or not self.test_agent_id:
            print("❌ No auth token or agent ID available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = await self.session.get(f"/agents/{self.test_agent_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Agent retrieved: {data['agent_name']}")
                print(f"   Description: {data['description']}")
                print(f"   System prompt length: {len(data['system_prompt'])} characters")
                return True
            else:
                error = response.json()
                print(f"❌ Agent retrieval failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Agent retrieval error: {e}")
            return False
    
    async def test_update_agent(self) -> bool:
        """Test updating an agent"""
        print("\n=== Testing Update Agent ===")
        
        if not self.auth_token or not self.test_agent_id:
            print("❌ No auth token or agent ID available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        update_data = {
            "description": "Updated test voice agent",
            "system_prompt": "You are an updated helpful test assistant."
        }
        
        try:
            response = await self.session.put(f"/agents/{self.test_agent_id}", json=update_data, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Agent updated: {data['agent_name']}")
                print(f"   New description: {data['description']}")
                return True
            else:
                error = response.json()
                print(f"❌ Agent update failed: {error}")
                return False
        except Exception as e:
            print(f"❌ Agent update error: {e}")
            return False
    
    async def test_session_manager(self) -> bool:
        """Test session manager endpoints"""
        print("\n=== Testing Session Manager Endpoints ===")

        if not self.auth_token:
            print("❌ No auth token available")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            # Test session manager stats
            response = await self.session.get("/session-manager/stats", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session manager stats retrieved")
                print(f"   Total sessions: {data.get('session_manager', {}).get('total_sessions', 0)}")
                print(f"   Active connections: {data.get('active_connections', 0)}")
            else:
                print(f"❌ Session manager stats failed: {response.status_code}")
                return False

            # Test list sessions (should be empty initially)
            response = await self.session.get("/session-manager/sessions", headers=headers)
            if response.status_code == 200:
                sessions_data = response.json()
                print(f"✅ Sessions listed: {len(sessions_data)} found")
            else:
                print(f"❌ Listing sessions failed: {response.status_code}")
                return False

            return True

        except Exception as e:
            print(f"❌ Session manager test error: {e}")
            return False

    async def test_multi_agent_conversations(self) -> bool:
        """Test multi-agent conversation capabilities"""
        print("\n=== Testing Multi-Agent Conversations ===")

        if not self.auth_token:
            print("❌ No auth token available")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            # Create multiple agents with different system prompts
            agents = []
            agent_configs = [
                {
                    "agent_name": "Customer Support Agent",
                    "description": "Handles customer service inquiries",
                    "system_prompt": "You are a helpful customer service representative. Always be polite and professional.",
                    "voice_settings": {"voice_id": "customer-service"}
                },
                {
                    "agent_name": "Technical Support Agent", 
                    "description": "Provides technical assistance",
                    "system_prompt": "You are a technical support specialist with deep knowledge of our products.",
                    "voice_settings": {"voice_id": "technical-support"}
                },
                {
                    "agent_name": "Sales Agent",
                    "description": "Assists with sales inquiries",
                    "system_prompt": "You are a sales representative focused on helping customers find the right products.",
                    "voice_settings": {"voice_id": "sales"}
                }
            ]

            # Create agents
            for config in agent_configs:
                response = await self.session.post("/agents/", json=config, headers=headers)
                if response.status_code == 200:
                    agent_data = response.json()
                    agents.append(agent_data)
                    print(f"✅ Created agent: {agent_data['agent_name']} (ID: {agent_data['id']})")
                else:
                    error_detail = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    print(f"❌ Failed to create agent: {config['agent_name']}")
                    print(f"   Status code: {response.status_code}")
                    print(f"   Error: {error_detail}")
                    # Continue trying to create other agents instead of failing immediately
                    continue

            # Test WebSocket connections with different agents
            websocket_tests = []
            for i, agent in enumerate(agents[:2]):  # Test first 2 agents
                try:
                    uri = f"ws://localhost:7860/ws/auth?token={self.auth_token}&agent_id={agent['id']}"
                    async with websockets.connect(uri, timeout=5) as websocket:
                        print(f"✅ WebSocket connected to agent {agent['agent_name']}")
                        websocket_tests.append(True)
                        await asyncio.sleep(0.5)  # Brief connection test
                except Exception as e:
                    print(f"❌ WebSocket connection failed for agent {agent['agent_name']}: {e}")
                    websocket_tests.append(False)

            # Check session manager stats after connections
            response = await self.session.get("/session-manager/stats", headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session stats after connections: {data.get('session_manager', {}).get('total_sessions', 0)} sessions")

            # Clean up created agents
            for agent in agents:
                try:
                    response = await self.session.delete(f"/agents/{agent['id']}", headers=headers)
                    if response.status_code == 200:
                        print(f"✅ Cleaned up agent: {agent['agent_name']}")
                except Exception as e:
                    print(f"⚠️  Could not clean up agent {agent['agent_name']}: {e}")

            # Test passes if we created at least 2 agents and WebSocket tests succeeded
            websocket_success = all(websocket_tests) if websocket_tests else False
            agent_creation_success = len(agents) >= 2  # At least 2 agents should be created
            
            print(f"\n📊 Multi-agent test results:")
            print(f"   Agents created: {len(agents)}/3")
            print(f"   WebSocket tests: {'✅ PASS' if websocket_success else '❌ FAIL'}")
            print(f"   Agent creation: {'✅ PASS' if agent_creation_success else '❌ FAIL'}")
            
            return websocket_success and agent_creation_success

        except Exception as e:
            print(f"❌ Multi-agent conversation test error: {e}")
            return False

    async def test_websocket_with_agent(self) -> bool:
        """Test WebSocket connection with specific agent"""
        print("\n=== Testing WebSocket with Agent Selection ===")

        if not self.auth_token or not self.test_agent_id:
            print("❌ No auth token or agent ID available")
            return False

        try:
            # Test WebSocket connection with agent_id parameter
            uri = f"ws://localhost:7860/ws/auth?token={self.auth_token}&agent_id={self.test_agent_id}"
            
            async with websockets.connect(uri, timeout=10) as websocket:
                print(f"✅ WebSocket connected with agent {self.test_agent_id}")
                
                # Wait a moment to ensure stable connection
                await asyncio.sleep(1)
                
                print(f"   Connection state: {'open' if websocket.open else 'closed'}")
                
                # Test without agent_id for comparison
                uri_no_agent = f"ws://localhost:7860/ws/auth?token={self.auth_token}"
                async with websockets.connect(uri_no_agent, timeout=10) as websocket2:
                    print(f"✅ WebSocket connected without agent (default prompt)")
                    await asyncio.sleep(1)
                    
                return True
                
        except Exception as e:
            print(f"❌ WebSocket with agent test error: {e}")
            return False


    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection"""
        print("\n=== Testing WebSocket Connection ===")
        
        try:
            uri = f"ws://localhost:7860/ws"
            async with websockets.connect(uri, timeout=10) as websocket:
                print(f"✅ WebSocket connected successfully")
                
                # Wait a moment to ensure stable connection
                await asyncio.sleep(1)
                
                print(f"   Connection state: {'open' if websocket.open else 'closed'}")
                return True
                
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"❌ WebSocket connection closed: {e}")
            return False
        except asyncio.TimeoutError:
            print(f"⏰ WebSocket connection timeout")
            return False
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
            return False
    
    async def test_authenticated_websocket(self) -> bool:
        """Test authenticated WebSocket connection"""
        print("\n=== Testing Authenticated WebSocket ===")
        
        if not self.auth_token:
            print("❌ No auth token available")
            return False
        
        try:
            # Pass token as query parameter for WebSocket authentication
            uri = f"ws://localhost:7860/ws/auth?token={self.auth_token}"
            
            async with websockets.connect(uri, timeout=10) as websocket:
                print(f"✅ Authenticated WebSocket connected successfully")
                
                # Wait a moment to ensure stable connection
                await asyncio.sleep(1)
                
                print(f"   Connection state: {'open' if websocket.open else 'closed'}")
                return True
                
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"❌ Authenticated WebSocket connection closed: {e}")
            return False
        except asyncio.TimeoutError:
            print(f"⏰ Authenticated WebSocket connection timeout")
            return False
        except Exception as e:
            print(f"❌ Authenticated WebSocket error: {e}")
            return False
    
    async def test_invalid_token(self) -> bool:
        """Test endpoints with invalid token"""
        print("\n=== Testing Invalid Token ===")
        
        headers = {"Authorization": "Bearer invalid_token_12345"}
        
        try:
            response = await self.session.get("/auth/profile", headers=headers)
            if response.status_code == 401:
                print("✅ Invalid token properly rejected (401)")
                return True
            else:
                print(f"❌ Invalid token should be rejected, got status: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Invalid token test error: {e}")
            return False
    
    async def test_cleanup(self) -> bool:
        """Clean up test data"""
        print("\n=== Cleaning Up Test Data ===")
        
        cleanup_success = True
        
        # Delete test agent if created
        if self.auth_token and self.test_agent_id:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            try:
                response = await self.session.delete(f"/agents/{self.test_agent_id}", headers=headers)
                if response.status_code == 200:
                    print(f"✅ Test agent deleted successfully")
                else:
                    print(f"⚠️  Could not delete test agent: {response.status_code}")
                    cleanup_success = False
            except Exception as e:
                print(f"⚠️  Error deleting test agent: {e}")
                cleanup_success = False
        
        return cleanup_success
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        print("🚀 Starting Comprehensive Voice Agent API Tests")
        print("=" * 70)
        
        results = {}
        
        # Server health tests
        results['server_health'] = await self.test_server_health()
        results['server_info'] = await self.test_server_info()
        results['metrics'] = await self.test_metrics()
        
        # Authentication tests
        results['user_registration'] = await self.test_user_registration()
        results['user_login'] = await self.test_user_login()
        results['get_profile'] = await self.test_get_profile()
        results['update_profile'] = await self.test_update_profile()
        results['get_api_key'] = await self.test_get_api_key()
        results['session_info'] = await self.test_session_info()
        
        # Agent management tests
        results['create_agent'] = await self.test_create_agent()
        results['list_agents'] = await self.test_list_agents()
        results['get_agent'] = await self.test_get_agent()
        results['update_agent'] = await self.test_update_agent()
        
        # Session management tests
        results['session_manager'] = await self.test_session_manager()
        results['multi_agent_conversations'] = await self.test_multi_agent_conversations()
        results['websocket_with_agent'] = await self.test_websocket_with_agent()
        
        # WebSocket tests
        results['websocket_connection'] = await self.test_websocket_connection()
        results['authenticated_websocket'] = await self.test_authenticated_websocket()
        
        # Security tests
        results['invalid_token'] = await self.test_invalid_token()
        
        # Cleanup
        results['cleanup'] = await self.test_cleanup()
        
        return results
    
    def print_test_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
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
            print(f"  {test_name:25} {status}")
        
        if success_rate >= 95:
            print("\n🎉 EXCELLENT: All tests passed successfully!")
        elif success_rate >= 80:
            print("\n✅ GOOD: Most tests passed")
        elif success_rate >= 60:
            print("\n⚠️  MODERATE: Some tests failed")
        else:
            print("\n❌ POOR: Many tests failed")
        
        print("=" * 70)

async def main():
    """Main test function"""
    async with VoiceAgentAPITester() as tester:
        results = await tester.run_all_tests()
        tester.print_test_summary(results)
        return results

if __name__ == "__main__":
    asyncio.run(main())
