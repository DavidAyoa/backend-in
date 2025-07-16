#!/usr/bin/env python3
"""
Pytest integration test file for Voice Agent Backend
Converts the comprehensive test suite to proper pytest format
"""

import pytest
import asyncio
import httpx
import websockets
import json
import time
import random
import string
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:7860"
WS_URL = "ws://localhost:7860"

def generate_test_email() -> str:
    """Generate a unique test email"""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_string}@example.com"

def generate_test_username() -> str:
    """Generate a unique test username"""
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"testuser_{random_string}"

class TestVoiceAgentAPI:
    """Pytest-compatible test class for Voice Agent API"""

    @pytest.mark.asyncio
    async def test_server_health(self):
        """Test server health endpoint"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "warning", "critical"]
            assert "timestamp" in data
            assert "server_info" in data

    @pytest.mark.asyncio
    async def test_server_info(self):
        """Test server info endpoint"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Voice Agent Server"
            assert "version" in data
            assert "features" in data
            assert isinstance(data["features"], list)

    @pytest.mark.asyncio
    async def test_metrics(self):
        """Test metrics endpoint"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            response = await client.get("/metrics")
            assert response.status_code == 200
            data = response.json()
            assert "connections" in data
            assert "performance" in data
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_user_registration_and_login(self):
        """Test user registration and login flow"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Generate test user data
            test_user_data = {
                "email": generate_test_email(),
                "username": generate_test_username(),
                "password": "password123",
                "full_name": "Test User"
            }
            
            # Test registration
            response = await client.post("/auth/register", json=test_user_data)
            assert response.status_code == 200
            data = response.json()
            assert "user" in data
            assert "token" in data
            assert data["user"]["username"] == test_user_data["username"]
            
            # Test login
            login_data = {
                "email_or_username": test_user_data["email"],
                "password": test_user_data["password"]
            }
            response = await client.post("/auth/login", json=login_data)
            assert response.status_code == 200
            data = response.json()
            assert "user" in data
            assert "token" in data
            assert data["user"]["username"] == test_user_data["username"]

    @pytest.mark.asyncio
    async def test_authenticated_endpoints(self):
        """Test authenticated endpoints"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Register user and get token
            test_user_data = {
                "email": generate_test_email(),
                "username": generate_test_username(),
                "password": "password123",
                "full_name": "Test User"
            }
            
            response = await client.post("/auth/register", json=test_user_data)
            assert response.status_code == 200
            token = response.json()["token"]
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test profile endpoint
            response = await client.get("/auth/profile", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == test_user_data["username"]
            assert data["email"] == test_user_data["email"]
            
            # Test API key endpoint
            response = await client.get("/auth/api-key", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "api_key" in data
            assert data["api_key"].startswith("va_")
            
            # Test session info
            response = await client.get("/auth/session", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "agent_limit" in data
            assert "can_create_agents" in data

    @pytest.mark.asyncio
    async def test_agent_management(self):
        """Test agent management endpoints"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Register user and get token
            test_user_data = {
                "email": generate_test_email(),
                "username": generate_test_username(),
                "password": "password123",
                "full_name": "Test User"
            }
            
            response = await client.post("/auth/register", json=test_user_data)
            assert response.status_code == 200
            token = response.json()["token"]
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test agent creation
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
            
            response = await client.post("/agents/", json=agent_data, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["agent_name"] == agent_data["agent_name"]
            assert data["description"] == agent_data["description"]
            assert isinstance(data["voice_settings"], dict)
            agent_id = data["id"]
            
            # Test agent listing
            response = await client.get("/agents/", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            assert any(agent["id"] == agent_id for agent in data)
            
            # Test agent retrieval
            response = await client.get(f"/agents/{agent_id}", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == agent_id
            assert data["agent_name"] == agent_data["agent_name"]
            
            # Test agent update
            update_data = {
                "description": "Updated test voice agent"
            }
            response = await client.put(f"/agents/{agent_id}", json=update_data, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == update_data["description"]
            
            # Test agent deletion
            response = await client.delete(f"/agents/{agent_id}", headers=headers)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_manager_endpoints(self):
        """Test session manager endpoints"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # Register user and get token
            test_user_data = {
                "email": generate_test_email(),
                "username": generate_test_username(),
                "password": "password123",
                "full_name": "Test User"
            }
            
            response = await client.post("/auth/register", json=test_user_data)
            assert response.status_code == 200
            token = response.json()["token"]
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test session manager stats
            response = await client.get("/session-manager/stats", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "session_manager" in data
            assert "active_connections" in data
            assert "server_capacity" in data
            
            # Test session listing
            response = await client.get("/session-manager/sessions", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_websocket_connections(self):
        """Test WebSocket connections"""
        # Test basic WebSocket connection
        try:
            async with websockets.connect(f"{WS_URL}/ws", timeout=10) as websocket:
                assert websocket.open
                await asyncio.sleep(0.5)  # Brief connection test
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
        
        # Test authenticated WebSocket (would need proper token)
        # This is a basic connectivity test

    @pytest.mark.asyncio
    async def test_invalid_token_rejection(self):
        """Test that invalid tokens are properly rejected"""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            headers = {"Authorization": "Bearer invalid_token_12345"}
            
            response = await client.get("/auth/profile", headers=headers)
            assert response.status_code == 401

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
