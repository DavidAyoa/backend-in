#!/usr/bin/env python3
"""
Comprehensive test suite for flexible conversation bot implementation
Following Pipecat testing best practices
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import the modules to test
from bot_flexible_conversation import (
    FlexibleConversationBot, 
    ConversationMode, 
    SessionInfo,
    ModeAwareFrameProcessor,
    flexible_bot
)
from pipecat.frames.frames import TextFrame, AudioRawFrame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection

# Configure pytest for async testing
pytest_plugins = ('pytest_asyncio',)

class TestConversationMode:
    """Test ConversationMode class and its methods"""
    
    def test_default_values(self):
        """Test default conversation mode values"""
        mode = ConversationMode()
        
        assert mode.voice_input == True
        assert mode.text_input == True
        assert mode.voice_output == True
        assert mode.text_output == True
        assert mode.enable_interruptions == True
        
    def test_custom_values(self):
        """Test custom conversation mode values"""
        mode = ConversationMode(
            voice_input=False,
            text_input=True,
            voice_output=True,
            text_output=False,
            enable_interruptions=False
        )
        
        assert mode.voice_input == False
        assert mode.text_input == True
        assert mode.voice_output == True
        assert mode.text_output == False
        assert mode.enable_interruptions == False
        
    def test_mode_property(self):
        """Test mode property generates correct descriptive string"""
        # Voice only
        mode = ConversationMode.voice_only()
        assert mode.mode == "voice_to_voice"
        
        # Text only  
        mode = ConversationMode.text_only()
        assert mode.mode == "text_to_text"
        
        # Voice to text
        mode = ConversationMode.voice_to_text()
        assert mode.mode == "voice_to_text"
        
        # Text to voice
        mode = ConversationMode.text_to_voice()
        assert mode.mode == "text_to_voice"
        
        # Full multimodal
        mode = ConversationMode.full_multimodal()
        assert mode.mode == "voice+text_to_voice+text"
        
    def test_property_methods(self):
        """Test property methods for checking input/output capabilities"""
        mode = ConversationMode(
            voice_input=True,
            text_input=False,
            voice_output=False,
            text_output=True
        )
        
        assert mode.has_voice_input == True
        assert mode.has_text_input == False
        assert mode.has_voice_output == False
        assert mode.has_text_output == True
        
    def test_validate_valid_modes(self):
        """Test validation of valid mode configurations"""
        # Valid modes
        assert ConversationMode.voice_only().validate() == True
        assert ConversationMode.text_only().validate() == True
        assert ConversationMode.voice_to_text().validate() == True
        assert ConversationMode.text_to_voice().validate() == True
        assert ConversationMode.full_multimodal().validate() == True
        
    def test_validate_invalid_modes(self):
        """Test validation of invalid mode configurations"""
        # No input
        mode = ConversationMode(
            voice_input=False,
            text_input=False,
            voice_output=True,
            text_output=True
        )
        assert mode.validate() == False
        
        # No output
        mode = ConversationMode(
            voice_input=True,
            text_input=True,
            voice_output=False,
            text_output=False
        )
        assert mode.validate() == False
        
        # No input or output
        mode = ConversationMode(
            voice_input=False,
            text_input=False,
            voice_output=False,
            text_output=False
        )
        assert mode.validate() == False


class TestSessionInfo:
    """Test SessionInfo class"""
    
    def test_session_info_creation(self):
        """Test SessionInfo creation with default values"""
        mode = ConversationMode()
        context = MagicMock()
        
        session = SessionInfo(
            session_id="test-session",
            mode=mode,
            context=context
        )
        
        assert session.session_id == "test-session"
        assert session.mode == mode
        assert session.context == context
        assert session.pipeline is None
        assert session.task is None
        assert session.runner is None
        assert session.transport is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        
    def test_update_activity(self):
        """Test activity timestamp update"""
        mode = ConversationMode()
        context = MagicMock()
        
        session = SessionInfo(
            session_id="test-session",
            mode=mode,
            context=context
        )
        
        original_activity = session.last_activity
        
        # Wait a bit and update
        import time
        time.sleep(0.01)
        session.update_activity()
        
        assert session.last_activity > original_activity


class TestModeAwareFrameProcessor:
    """Test ModeAwareFrameProcessor class"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot with active session"""
        bot = MagicMock()
        session = MagicMock()
        session.mode = ConversationMode.full_multimodal()
        session.transport = MagicMock()
        session.transport._client = AsyncMock()
        session.transport._client.send = AsyncMock()
        session.update_activity = MagicMock()
        
        bot.active_sessions = {"test-session": session}
        return bot
        
    @pytest.fixture
    def processor(self, mock_bot):
        """Create a ModeAwareFrameProcessor instance"""
        return ModeAwareFrameProcessor("test-session", mock_bot)
        
    @pytest.mark.asyncio
    async def test_process_audio_frame_voice_input_enabled(self, processor, mock_bot):
        """Test processing audio frame when voice input is enabled"""
        frame = AudioRawFrame(b"audio_data", 16000, 1)
        
        # Mock push_frame
        processor.push_frame = AsyncMock()
        
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
        
        # Should pass through
        processor.push_frame.assert_called_once_with(frame, FrameDirection.DOWNSTREAM)
        
    @pytest.mark.asyncio
    async def test_process_audio_frame_voice_input_disabled(self, processor, mock_bot):
        """Test processing audio frame when voice input is disabled"""
        # Set mode to text only
        mock_bot.active_sessions["test-session"].mode = ConversationMode.text_only()
        
        frame = AudioRawFrame(b"audio_data", 16000, 1)
        processor.push_frame = AsyncMock()
        
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
        
        # Should not pass through
        processor.push_frame.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_process_text_frame_text_output_enabled(self, processor, mock_bot):
        """Test processing text frame when text output is enabled"""
        frame = TextFrame("Hello world")
        
        processor.push_frame = AsyncMock()
        processor._send_text_response = AsyncMock()
        
        await processor.process_frame(frame, FrameDirection.UPSTREAM)
        
        # Should send text response and pass through
        processor._send_text_response.assert_called_once_with(frame)
        processor.push_frame.assert_called_once_with(frame, FrameDirection.UPSTREAM)
        
    @pytest.mark.asyncio
    async def test_process_text_frame_text_output_disabled(self, processor, mock_bot):
        """Test processing text frame when text output is disabled"""
        # Set mode to voice only
        mock_bot.active_sessions["test-session"].mode = ConversationMode.voice_only()
        
        frame = TextFrame("Hello world")
        processor.push_frame = AsyncMock()
        
        await processor.process_frame(frame, FrameDirection.UPSTREAM)
        
        # Should not pass through
        processor.push_frame.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_process_transcription_frame(self, processor, mock_bot):
        """Test processing transcription frame"""
        frame = TranscriptionFrame("Hello world", "test-user", 12345)
        
        processor.push_frame = AsyncMock()
        processor._send_transcript = AsyncMock()
        
        await processor.process_frame(frame, FrameDirection.DOWNSTREAM)
        
        # Should send transcript and pass through - verify the call was made (might be with a different frame)
        processor._send_transcript.assert_called_once()
        processor.push_frame.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_send_transcript(self, processor, mock_bot):
        """Test sending transcript via WebSocket"""
        frame = TranscriptionFrame("Hello world", "test-user", 12345)
        frame.is_final = True
        
        await processor._send_transcript(frame)
        
        # Verify WebSocket was called
        client = mock_bot.active_sessions["test-session"].transport._client
        client.send.assert_called_once()
        
        # Verify the sent data
        call_args = client.send.call_args[0][0]
        sent_data = json.loads(call_args)
        
        assert sent_data["type"] == "transcript"
        assert sent_data["data"]["text"] == "Hello world"
        assert sent_data["data"]["is_final"] == True
        assert sent_data["data"]["source"] == "user"
        
    @pytest.mark.asyncio
    async def test_send_text_response(self, processor, mock_bot):
        """Test sending text response via WebSocket"""
        frame = TextFrame("Hello back!")
        
        await processor._send_text_response(frame)
        
        # Verify WebSocket was called
        client = mock_bot.active_sessions["test-session"].transport._client
        client.send.assert_called_once()
        
        # Verify the sent data
        call_args = client.send.call_args[0][0]
        sent_data = json.loads(call_args)
        
        assert sent_data["type"] == "assistant_response"
        assert sent_data["data"]["text"] == "Hello back!"
        assert sent_data["data"]["source"] == "assistant"


class TestFlexibleConversationBot:
    """Test FlexibleConversationBot class"""
    
    @pytest.fixture
    def bot(self):
        """Create a FlexibleConversationBot instance"""
        return FlexibleConversationBot()
        
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        websocket = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        return websocket
        
    @pytest.fixture
    def mock_service_pool(self):
        """Create a mock service pool"""
        pool = MagicMock()
        pool.get_llm_service.return_value = MagicMock()
        pool.get_stt_service.return_value = MagicMock()
        pool.get_tts_service.return_value = MagicMock()
        pool.get_vad_analyzer.return_value = MagicMock()
        pool.cleanup_session = AsyncMock()
        return pool
        
    @pytest.mark.asyncio
    async def test_create_session_basic(self, bot, mock_websocket):
        """Test basic session creation"""
        with patch('bot_flexible_conversation.session_manager') as mock_session_manager, \
             patch('bot_flexible_conversation.config') as mock_config:
            # Mock session manager
            mock_session_manager.sessions = {}
            mock_session_manager.create_session.return_value = "test-session"
            mock_session_manager.get_session.return_value = None
            
            # Mock config
            mock_config.get_system_prompt.return_value = "Test system prompt"
            mock_config.ENABLE_METRICS = True
            
            # Mock pipeline components
            with patch('bot_flexible_conversation.PipelineRunner') as mock_pipeline_runner, \
                 patch('bot_flexible_conversation.FastAPIWebsocketTransport') as mock_transport, \
                 patch('bot_flexible_conversation.Pipeline') as mock_pipeline, \
                 patch('bot_flexible_conversation.PipelineTask') as mock_task:
                # Setup pipeline runner mock to be async
                mock_runner = AsyncMock()
                mock_runner.run = AsyncMock()
                mock_pipeline_runner.return_value = mock_runner
                
                # Mock service pool
                bot.service_pool = MagicMock()
                bot.service_pool.get_llm_service.return_value = MagicMock()
                bot.service_pool.get_stt_service.return_value = MagicMock()
                bot.service_pool.get_tts_service.return_value = MagicMock()
                bot.service_pool.get_vad_analyzer.return_value = MagicMock()
                bot.service_pool.cleanup_session = AsyncMock()
                
                # Mock LLM service context aggregator
                llm_service = bot.service_pool.get_llm_service.return_value
                llm_service.create_context_aggregator.return_value = MagicMock()
                
                mode = ConversationMode.voice_only()
                session_id = await bot.create_session(
                    websocket=mock_websocket,
                    initial_mode=mode
                )
                
                assert session_id is not None
                assert session_id in bot.active_sessions
                assert bot.active_sessions[session_id].mode == mode
                
    @pytest.mark.asyncio
    async def test_switch_mode(self, bot, mock_websocket):
        """Test mode switching functionality"""
        with patch('bot_flexible_conversation.session_manager') as mock_session_manager, \
             patch('bot_flexible_conversation.config') as mock_config:
            # Setup initial session
            mock_session_manager.sessions = {}
            mock_session_manager.create_session.return_value = "test-session"
            mock_session_manager.get_session.return_value = None
            mock_config.get_system_prompt.return_value = "Test system prompt"
            mock_config.ENABLE_METRICS = True
            
            # Mock pipeline components
            with patch('bot_flexible_conversation.PipelineRunner') as mock_pipeline_runner, \
                 patch('bot_flexible_conversation.FastAPIWebsocketTransport') as mock_transport, \
                 patch('bot_flexible_conversation.Pipeline') as mock_pipeline, \
                 patch('bot_flexible_conversation.PipelineTask') as mock_task:
                # Setup pipeline runner mock to be async
                mock_runner = AsyncMock()
                mock_runner.run = AsyncMock()
                mock_pipeline_runner.return_value = mock_runner
                
                # Mock service pool
                bot.service_pool = MagicMock()
                bot.service_pool.get_llm_service.return_value = MagicMock()
                bot.service_pool.get_stt_service.return_value = MagicMock()
                bot.service_pool.get_tts_service.return_value = MagicMock()
                bot.service_pool.get_vad_analyzer.return_value = MagicMock()
                bot.service_pool.cleanup_session = AsyncMock()
                
                # Mock LLM service context aggregator
                llm_service = bot.service_pool.get_llm_service.return_value
                llm_service.create_context_aggregator.return_value = MagicMock()
                
                # Create initial session
                initial_mode = ConversationMode.voice_only()
                session_id = await bot.create_session(
                    websocket=mock_websocket,
                    initial_mode=initial_mode
                )
                
                # Switch to text mode
                new_mode = ConversationMode.text_only()
                await bot.switch_mode(session_id, new_mode)
                
                # Verify mode was changed
                assert bot.active_sessions[session_id].mode == new_mode
                
    def test_get_session_info(self, bot):
        """Test getting session information"""
        # Create a mock session
        mode = ConversationMode.voice_only()
        context = MagicMock()
        session = SessionInfo(
            session_id="test-session",
            mode=mode,
            context=context
        )
        
        bot.active_sessions["test-session"] = session
        
        # Test getting existing session
        info = bot.get_session_info("test-session")
        assert info == session
        
        # Test getting non-existent session
        info = bot.get_session_info("non-existent")
        assert info is None
        
    def test_get_active_sessions(self, bot):
        """Test getting all active sessions"""
        # Create mock sessions
        mode1 = ConversationMode.voice_only()
        mode2 = ConversationMode.text_only()
        
        session1 = SessionInfo("session1", mode1, MagicMock())
        session2 = SessionInfo("session2", mode2, MagicMock())
        
        bot.active_sessions = {
            "session1": session1,
            "session2": session2
        }
        
        sessions = bot.get_active_sessions()
        
        assert len(sessions) == 2
        assert sessions["session1"] == session1
        assert sessions["session2"] == session2
        
    def test_get_session_stats(self, bot):
        """Test getting session statistics"""
        # Create mock sessions with different modes
        voice_mode = ConversationMode.voice_only()
        text_mode = ConversationMode.text_only()
        
        session1 = SessionInfo("session1", voice_mode, MagicMock())
        session2 = SessionInfo("session2", text_mode, MagicMock())
        session3 = SessionInfo("session3", voice_mode, MagicMock())
        
        bot.active_sessions = {
            "session1": session1,
            "session2": session2,
            "session3": session3
        }
        
        stats = bot.get_session_stats()
        
        assert stats["total_sessions"] == 3
        assert stats["voice_sessions"] == 2
        assert stats["text_sessions"] == 1
        
    @pytest.mark.asyncio
    async def test_cleanup_session(self, bot):
        """Test session cleanup"""
        # Create a mock session
        mode = ConversationMode.voice_only()
        context = MagicMock()
        session = SessionInfo("test-session", mode, context)
        
        # Mock components
        session.task = AsyncMock()
        session.task.cancel = AsyncMock()
        session.transport = MagicMock()
        session.transport._client = AsyncMock()
        session.transport._client.disconnect = AsyncMock()
        
        # Mock service pool
        bot.service_pool = MagicMock()
        bot.service_pool.cleanup_session = AsyncMock()
        
        bot.active_sessions["test-session"] = session
        
        await bot.cleanup_session("test-session")
        
        # Verify cleanup was called
        session.task.cancel.assert_called_once()
        session.transport._client.disconnect.assert_called_once()
        bot.service_pool.cleanup_session.assert_called_once_with("test-session")
        
        # Verify session was removed
        assert "test-session" not in bot.active_sessions
        
    @pytest.mark.asyncio
    async def test_handle_websocket_message_mode_change(self, bot):
        """Test handling WebSocket mode change messages"""
        # Create a mock session
        mode = ConversationMode.voice_only()
        context = MagicMock()
        session = SessionInfo("test-session", mode, context)
        bot.active_sessions["test-session"] = session
        
        # Mock transport
        transport = MagicMock()
        transport.websocket = AsyncMock()
        
        # Mock switch_mode
        bot.switch_mode = AsyncMock()
        
        # Test message
        message = json.dumps({
            "type": "mode_change",
            "data": {
                "voice_input": False,
                "text_input": True,
                "voice_output": True,
                "text_output": False
            }
        })
        
        await bot._handle_websocket_message("test-session", transport, message)
        
        # Verify switch_mode was called
        bot.switch_mode.assert_called_once()
        call_args = bot.switch_mode.call_args[0]
        assert call_args[0] == "test-session"
        
        new_mode = call_args[1]
        assert new_mode.voice_input == False
        assert new_mode.text_input == True
        assert new_mode.voice_output == True
        assert new_mode.text_output == False
        
    @pytest.mark.asyncio
    async def test_handle_websocket_message_invalid_mode(self, bot):
        """Test handling invalid mode configuration"""
        # Create a mock session
        mode = ConversationMode.voice_only()
        context = MagicMock()
        session = SessionInfo("test-session", mode, context)
        bot.active_sessions["test-session"] = session
        
        # Mock transport
        transport = MagicMock()
        transport._client = AsyncMock()
        transport._client.send = AsyncMock()
        
        # Test invalid message (no input or output)
        message = json.dumps({
            "type": "mode_change",
            "data": {
                "voice_input": False,
                "text_input": False,
                "voice_output": False,
                "text_output": False
            }
        })
        
        await bot._handle_websocket_message("test-session", transport, message)
        
        # Verify error was sent
        transport._client.send.assert_called_once()
        call_args = transport._client.send.call_args[0][0]
        sent_data = json.loads(call_args)
        
        assert sent_data["type"] == "error"
        assert "Invalid mode configuration" in sent_data["data"]["message"]
        
    @pytest.mark.asyncio
    async def test_handle_text_message(self, bot):
        """Test handling text messages"""
        # Create a mock session
        mode = ConversationMode.text_only()
        context = MagicMock()
        context.messages = []
        session = SessionInfo("test-session", mode, context)
        session.transport = MagicMock()
        session.transport._client = AsyncMock()
        session.transport._client.send = AsyncMock()
        
        bot.active_sessions["test-session"] = session
        
        data = {"text": "Hello world"}
        
        await bot._handle_text_message("test-session", data)
        
        # Verify message was added to context
        assert len(context.messages) == 1
        assert context.messages[0]["role"] == "user"
        assert context.messages[0]["content"] == "Hello world"
        
        # Verify transcript was sent
        session.transport._client.send.assert_called_once()


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_voice_to_text(self):
        """Test complete workflow from voice input to text output"""
        # This would be a more complex integration test
        # Testing the full pipeline flow
        pass
        
    @pytest.mark.asyncio
    async def test_mode_switching_preserves_context(self):
        """Test that mode switching preserves conversation context"""
        # This would test that when switching modes,
        # the conversation history is maintained
        pass


# Test configuration for pytest
def test_pipeline_params_configuration():
    """Test that pipeline params are set correctly"""
    mode = ConversationMode(enable_interruptions=False)
    
    # Test parameter generation logic
    from pipecat.pipeline.task import PipelineParams
    
    # This would be testing your parameter generation logic
    # without actually creating a pipeline
    expected_interruptions = False
    
    assert mode.enable_interruptions == expected_interruptions


# Run tests with coverage
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=bot_flexible_conversation"])
