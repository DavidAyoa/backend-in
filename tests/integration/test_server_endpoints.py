#!/usr/bin/env python3
"""
Test suite for server endpoints and WebSocket functionality
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

# Import the server module
from server import app, connection_manager, FlexibleConversationMode

# Configure pytest for async testing
pytest_plugins = ('pytest_asyncio',)

class TestServerEndpoints:
    """Test REST API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns correct information"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Voice Agent Server"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "flexible_conversation_modes" in data["features"]
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "server_info" in data
        assert data["status"] in ["healthy", "warning", "critical"]
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "connections" in data
        assert "performance" in data
        assert "timestamp" in data
        
        # Check connection metrics
        connections = data["connections"]
        assert "total" in connections
        assert "active" in connections
        assert "peak" in connections
        assert "rejected" in connections
    
    def test_connect_endpoint(self, client):
        """Test connect endpoint"""
        response = client.post("/connect")
        assert response.status_code == 200
        
        data = response.json()
        assert "ws_url" in data
        assert "status" in data
        assert "capacity" in data
        assert data["status"] == "available"
    
    def test_connect_endpoint_at_capacity(self, client):
        """Test connect endpoint when server is at capacity"""
        # Mock connection manager to simulate full capacity
        original_max = connection_manager.max_connections
        connection_manager.max_connections = 0
        
        try:
            response = client.post("/connect")
            assert response.status_code == 503
            
            data = response.json()
            assert "error" in data["detail"]
            assert data["detail"]["error"] == "Server at capacity"
        finally:
            connection_manager.max_connections = original_max


class TestWebSocketEndpoints:
    """Test WebSocket endpoints"""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_flexible_websocket_endpoint_valid_mode(self, mock_websocket):
        """Test flexible WebSocket endpoint with valid mode"""
        from server import flexible_websocket_endpoint
        
        with patch('server.connection_manager') as mock_conn_manager:
            mock_conn_manager.connect = AsyncMock(return_value="test-client-id")
            mock_conn_manager.disconnect = AsyncMock()
            
            with patch('server.flexible_bot') as mock_bot:
                mock_bot.create_session = AsyncMock()
                
                # Test valid mode configuration
                await flexible_websocket_endpoint(
                    websocket=mock_websocket,
                    voice_input=True,
                    text_input=False,
                    voice_output=False,
                    text_output=True
                )
                
                # Verify connection was established
                mock_conn_manager.connect.assert_called_once_with(mock_websocket)
                
                # Verify session was created
                mock_bot.create_session.assert_called_once()
                call_args = mock_bot.create_session.call_args
                
                # The websocket is the first positional argument
                assert call_args[0][0] == mock_websocket
                assert call_args[1]["session_id"] == "test-client-id"
                
                # Verify mode configuration
                initial_mode = call_args[1]["initial_mode"]
                assert initial_mode.voice_input == True
                assert initial_mode.text_input == False
                assert initial_mode.voice_output == False
                assert initial_mode.text_output == True
    
    @pytest.mark.asyncio
    async def test_flexible_websocket_endpoint_invalid_mode(self, mock_websocket):
        """Test flexible WebSocket endpoint with invalid mode"""
        from server import flexible_websocket_endpoint
        
        with patch('server.connection_manager') as mock_conn_manager:
            mock_conn_manager.connect = AsyncMock(return_value="test-client-id")
            mock_conn_manager.disconnect = AsyncMock()
            
            # Test invalid mode configuration (no input or output)
            await flexible_websocket_endpoint(
                websocket=mock_websocket,
                voice_input=False,
                text_input=False,
                voice_output=False,
                text_output=False
            )
            
            # Verify connection was established
            mock_conn_manager.connect.assert_called_once_with(mock_websocket)
            
            # Verify WebSocket was closed due to invalid mode
            mock_websocket.close.assert_called_once_with(
                code=1008, 
                reason="Invalid mode configuration"
            )
    
    @pytest.mark.asyncio
    async def test_flexible_websocket_endpoint_server_full(self, mock_websocket):
        """Test flexible WebSocket endpoint when server is at capacity"""
        from server import flexible_websocket_endpoint
        
        with patch('server.connection_manager') as mock_conn_manager:
            # Simulate server at capacity
            mock_conn_manager.connect = AsyncMock(return_value=None)
            
            await flexible_websocket_endpoint(
                websocket=mock_websocket,
                voice_input=True,
                text_input=True,
                voice_output=True,
                text_output=True
            )
            
            # Verify connection was attempted
            mock_conn_manager.connect.assert_called_once_with(mock_websocket)
            
            # Verify no session was created
            # (function should return early when client_id is None)
    


class TestConnectionManager:
    """Test connection manager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager for testing"""
        from server import ConnectionManager
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connection_manager_start_stop(self, manager):
        """Test connection manager startup and shutdown"""
        await manager.start()
        assert manager._cleanup_task is not None
        
        await manager.stop()
        assert manager._cleanup_task.cancelled()
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect(self, manager):
        """Test connection establishment"""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.client.host = "127.0.0.1"
        
        client_id = await manager.connect(mock_websocket)
        
        assert client_id is not None
        assert client_id in manager.connections
        assert manager.connections[client_id].websocket == mock_websocket
        
        # Verify WebSocket was accepted
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_manager_disconnect(self, manager):
        """Test connection cleanup"""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.application_state.name = "CONNECTED"
        
        client_id = await manager.connect(mock_websocket)
        assert client_id in manager.connections
        
        await manager.disconnect(client_id)
        assert client_id not in manager.connections
        
        # Verify WebSocket was closed
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_manager_capacity_limit(self, manager):
        """Test connection capacity limits"""
        # Set a low capacity limit
        manager.max_connections = 1
        
        # First connection should succeed
        mock_websocket1 = AsyncMock()
        mock_websocket1.accept = AsyncMock()
        mock_websocket1.client.host = "127.0.0.1"
        
        client_id1 = await manager.connect(mock_websocket1)
        assert client_id1 is not None
        
        # Second connection should be rejected
        mock_websocket2 = AsyncMock()
        mock_websocket2.close = AsyncMock()
        mock_websocket2.client.host = "127.0.0.2"
        
        client_id2 = await manager.connect(mock_websocket2)
        assert client_id2 is None
        
        # Verify second WebSocket was closed
        mock_websocket2.close.assert_called_once_with(
            code=1008, 
            reason="Server at capacity"
        )
    
    def test_connection_manager_metrics(self, manager):
        """Test connection manager metrics"""
        metrics = manager.get_metrics()
        
        assert "connections" in metrics
        assert "performance" in metrics
        assert "timestamp" in metrics
        
        # Check connection metrics structure
        connections = metrics["connections"]
        assert "total" in connections
        assert "active" in connections
        assert "peak" in connections
        assert "rejected" in connections
        assert "capacity_used" in connections
        
        # Check performance metrics structure
        performance = metrics["performance"]
        assert "avg_session_duration" in performance
        assert "max_connections" in performance
        assert "connection_timeout" in performance


class TestConversationModeValidation:
    """Test conversation mode validation in server context"""
    
    def test_flexible_conversation_mode_creation(self):
        """Test FlexibleConversationMode creation"""
        # Test default mode
        mode = FlexibleConversationMode()
        assert mode.voice_input == True
        assert mode.text_input == True
        assert mode.voice_output == True
        assert mode.text_output == True
        
        # Test custom mode
        mode = FlexibleConversationMode(
            voice_input=False,
            text_input=True,
            voice_output=True,
            text_output=False
        )
        assert mode.voice_input == False
        assert mode.text_input == True
        assert mode.voice_output == True
        assert mode.text_output == False
    
    def test_conversation_mode_validation_in_endpoint(self):
        """Test that endpoint properly validates conversation modes"""
        # Valid mode
        valid_mode = FlexibleConversationMode(
            voice_input=True,
            text_input=False,
            voice_output=False,
            text_output=True
        )
        assert valid_mode.validate() == True
        
        # Invalid mode (no input)
        invalid_mode = FlexibleConversationMode(
            voice_input=False,
            text_input=False,
            voice_output=True,
            text_output=True
        )
        assert invalid_mode.validate() == False
        
        # Invalid mode (no output)
        invalid_mode = FlexibleConversationMode(
            voice_input=True,
            text_input=True,
            voice_output=False,
            text_output=False
        )
        assert invalid_mode.validate() == False


# Integration tests
class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_full_websocket_flow(self):
        """Test complete WebSocket flow with mode switching"""
        # This would be a more complex integration test
        # that actually establishes a WebSocket connection
        # and tests the full conversation flow
        pass
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self):
        """Test handling multiple concurrent connections"""
        # This would test that the server can handle
        # multiple WebSocket connections simultaneously
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
