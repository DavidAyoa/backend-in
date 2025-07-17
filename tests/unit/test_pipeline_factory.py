#!/usr/bin/env python3
"""
Unit tests for bot pipeline factory
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os

from bot.pipeline_factory import (
    create_pipeline,
    create_pipeline_task,
    create_pipeline_runner,
    create_full_pipeline_setup
)
from transports.base import TransportConfig, TransportType
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext


class TestPipelineFactory:
    """Test pipeline factory functions"""
    
    @pytest.fixture
    def transport_config(self):
        """Create a test transport config"""
        return TransportConfig(
            transport_type=TransportType.WEBSOCKET,
            sample_rate=24000,
            enable_interruptions=True
        )
    
    @pytest.fixture
    def mock_transport(self):
        """Create a mock transport"""
        transport = MagicMock()
        transport.input.return_value = MagicMock()
        transport.output.return_value = MagicMock()
        return transport
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock OpenAI LLM context"""
        context = MagicMock(spec=OpenAILLMContext)
        context.get_messages.return_value = []
        context.add_message.return_value = None
        context.set_messages.return_value = None
        return context
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.GoogleSTTService')
    @patch('bot.pipeline_factory.OpenAILLMService')
    @patch('bot.pipeline_factory.GoogleTTSService')
    @patch('bot.pipeline_factory.Pipeline')
    @patch('bot.pipeline_factory.MinWordsInterruptionStrategy')
    async def test_create_pipeline_without_service_pool(
        self, 
        mock_interruption, 
        mock_pipeline, 
        mock_tts, 
        mock_llm, 
        mock_stt,
        mock_transport,
        mock_context,
        transport_config
    ):
        """Test creating pipeline without service pool"""
        # Setup mocks
        mock_stt_instance = MagicMock()
        mock_llm_instance = MagicMock()
        mock_tts_instance = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_interruption_instance = MagicMock()
        
        mock_stt.return_value = mock_stt_instance
        mock_llm.return_value = mock_llm_instance
        mock_tts.return_value = mock_tts_instance
        mock_pipeline.return_value = mock_pipeline_instance
        mock_interruption.return_value = mock_interruption_instance
        
        # Set environment variables
        with patch.dict('os.environ', {
            'GOOGLE_API_KEY': 'test-google-key',
            'OPENAI_API_KEY': 'test-openai-key'
        }):
            # Create pipeline
            pipeline = await create_pipeline(mock_transport, mock_context, transport_config)
        
        # Verify services were created
        mock_stt.assert_called_once()
        mock_llm.assert_called_once()
        mock_tts.assert_called_once()
        
        # Verify pipeline was created
        mock_pipeline.assert_called_once()
        
        # Verify interruption strategy was set
        mock_interruption.assert_called_once_with(min_words=1)
        mock_pipeline_instance.set_interruption_strategy.assert_called_once_with(mock_interruption_instance)
        
        assert pipeline == mock_pipeline_instance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.Pipeline')
    async def test_create_pipeline_with_service_pool(
        self, 
        mock_pipeline,
        mock_transport,
        mock_context,
        transport_config
    ):
        """Test creating pipeline with service pool"""
        # Create mock service pool
        mock_service_pool = AsyncMock()
        mock_stt = MagicMock()
        mock_llm = MagicMock()
        mock_tts = MagicMock()
        
        mock_service_pool.get_stt_service.return_value = mock_stt
        mock_service_pool.get_llm_service.return_value = mock_llm
        mock_service_pool.get_tts_service.return_value = mock_tts
        
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        
        # Create pipeline with service pool
        pipeline = await create_pipeline(
            mock_transport, 
            mock_context, 
            transport_config, 
            service_pool=mock_service_pool
        )
        
        # Verify services were retrieved from pool
        mock_service_pool.get_stt_service.assert_called_once()
        mock_service_pool.get_llm_service.assert_called_once()
        mock_service_pool.get_tts_service.assert_called_once()
        
        # Verify pipeline was created
        mock_pipeline.assert_called_once()
        assert pipeline == mock_pipeline_instance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.Pipeline')
    async def test_create_pipeline_fallback_structure(
        self, 
        mock_pipeline,
        mock_context,
        transport_config
    ):
        """Test creating pipeline with fallback structure for transport without input/output"""
        # Create transport without input/output methods
        mock_transport = MagicMock()
        del mock_transport.input
        del mock_transport.output
        
        mock_pipeline_instance = MagicMock()
        mock_pipeline.return_value = mock_pipeline_instance
        
        with patch('bot.pipeline_factory.GoogleSTTService'), \
             patch('bot.pipeline_factory.OpenAILLMService'), \
             patch('bot.pipeline_factory.GoogleTTSService'), \
             patch.dict('os.environ', {
                 'GOOGLE_API_KEY': 'test-key',
                 'OPENAI_API_KEY': 'test-key'
             }):
            
            pipeline = await create_pipeline(mock_transport, mock_context, transport_config)
        
        # Should still create pipeline with fallback structure
        mock_pipeline.assert_called_once()
        assert pipeline == mock_pipeline_instance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.PipelineTask')
    @patch('bot.pipeline_factory.PipelineParams')
    async def test_create_pipeline_task(self, mock_params, mock_task, transport_config):
        """Test creating pipeline task"""
        mock_pipeline = MagicMock()
        mock_params_instance = MagicMock()
        mock_task_instance = MagicMock()
        
        mock_params.return_value = mock_params_instance
        mock_task.return_value = mock_task_instance
        
        mock_transport = MagicMock()
        
        task = await create_pipeline_task(mock_pipeline, mock_transport, transport_config)
        
        # Verify params were created with correct settings
        mock_params.assert_called_once_with(
            allow_interruptions=transport_config.enable_interruptions,
            enable_metrics=True,
            enable_usage_metrics=True
        )
        
        # Verify task was created
        mock_task.assert_called_once_with(mock_pipeline, params=mock_params_instance)
        assert task == mock_task_instance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.PipelineRunner')
    async def test_create_pipeline_runner(self, mock_runner, transport_config):
        """Test creating pipeline runner"""
        mock_task = MagicMock()
        mock_transport = MagicMock()
        mock_runner_instance = MagicMock()
        
        mock_runner.return_value = mock_runner_instance
        
        runner = await create_pipeline_runner(mock_task, mock_transport, transport_config)
        
        # Verify runner was created
        mock_runner.assert_called_once()
        assert runner == mock_runner_instance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.create_pipeline')
    @patch('bot.pipeline_factory.create_pipeline_task')
    @patch('bot.pipeline_factory.create_pipeline_runner')
    async def test_create_full_pipeline_setup(
        self, 
        mock_create_runner,
        mock_create_task,
        mock_create_pipeline,
        mock_transport,
        mock_context,
        transport_config
    ):
        """Test creating full pipeline setup"""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_task = MagicMock()
        mock_runner = MagicMock()
        
        mock_create_pipeline.return_value = mock_pipeline
        mock_create_task.return_value = mock_task
        mock_create_runner.return_value = mock_runner
        
        # Create full setup
        pipeline, task, runner = await create_full_pipeline_setup(
            mock_transport, 
            mock_context, 
            transport_config
        )
        
        # Verify all components were created in order
        mock_create_pipeline.assert_called_once_with(
            mock_transport, mock_context, transport_config, None
        )
        mock_create_task.assert_called_once_with(
            mock_pipeline, mock_transport, transport_config
        )
        mock_create_runner.assert_called_once_with(
            mock_task, mock_transport, transport_config
        )
        
        # Verify return values
        assert pipeline == mock_pipeline
        assert task == mock_task
        assert runner == mock_runner
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.create_pipeline')
    @patch('bot.pipeline_factory.create_pipeline_task')
    @patch('bot.pipeline_factory.create_pipeline_runner')
    async def test_create_full_pipeline_setup_with_service_pool(
        self, 
        mock_create_runner,
        mock_create_task,
        mock_create_pipeline,
        mock_transport,
        mock_context,
        transport_config
    ):
        """Test creating full pipeline setup with service pool"""
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_task = MagicMock()
        mock_runner = MagicMock()
        mock_service_pool = MagicMock()
        
        mock_create_pipeline.return_value = mock_pipeline
        mock_create_task.return_value = mock_task
        mock_create_runner.return_value = mock_runner
        
        # Create full setup with service pool
        pipeline, task, runner = await create_full_pipeline_setup(
            mock_transport, 
            mock_context, 
            transport_config,
            service_pool=mock_service_pool
        )
        
        # Verify pipeline was created with service pool
        mock_create_pipeline.assert_called_once_with(
            mock_transport, mock_context, transport_config, mock_service_pool
        )
        
        # Verify return values
        assert pipeline == mock_pipeline
        assert task == mock_task
        assert runner == mock_runner


class TestPipelineEnvironmentConfiguration:
    """Test pipeline configuration from environment variables"""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.GoogleSTTService')
    @patch('bot.pipeline_factory.OpenAILLMService')
    @patch('bot.pipeline_factory.GoogleTTSService')
    @patch('bot.pipeline_factory.Pipeline')
    async def test_pipeline_with_custom_environment_config(
        self, 
        mock_pipeline, 
        mock_tts, 
        mock_llm, 
        mock_stt
    ):
        """Test pipeline creation with custom environment configuration"""
        # Setup mocks
        mock_stt_instance = MagicMock()
        mock_llm_instance = MagicMock()
        mock_tts_instance = MagicMock()
        mock_pipeline_instance = MagicMock()
        
        mock_stt.return_value = mock_stt_instance
        mock_llm.return_value = mock_llm_instance
        mock_tts.return_value = mock_tts_instance
        mock_pipeline.return_value = mock_pipeline_instance
        
        # Custom environment configuration
        custom_env = {
            'GOOGLE_API_KEY': 'custom-google-key',
            'OPENAI_API_KEY': 'custom-openai-key',
            'OPENAI_MODEL': 'gpt-4',
            'GOOGLE_STT_LANGUAGE': 'fr-FR',
            'GOOGLE_STT_MODEL': 'latest_short',
            'GOOGLE_TTS_VOICE': 'fr-FR-Standard-A'
        }
        
        config = TransportConfig(
            transport_type=TransportType.WEBSOCKET,
            sample_rate=48000
        )
        
        mock_transport = MagicMock()
        mock_transport.input.return_value = MagicMock()
        mock_transport.output.return_value = MagicMock()
        
        mock_context = MagicMock(spec=OpenAILLMContext)
        mock_context.get_messages.return_value = []
        mock_context.add_message.return_value = None
        mock_context.set_messages.return_value = None
        
        with patch.dict('os.environ', custom_env):
            pipeline = await create_pipeline(mock_transport, mock_context, config)
        
        # Verify services were created with custom configuration
        mock_stt.assert_called_once_with(
            api_key='custom-google-key',
            language='fr-FR',
            model='latest_short'
        )
        
        mock_llm.assert_called_once_with(
            api_key='custom-openai-key',
            model='gpt-4'
        )
        
        mock_tts.assert_called_once_with(
            api_key='custom-google-key',
            voice_id='fr-FR-Standard-A',
            sample_rate=48000
        )
        
        assert pipeline == mock_pipeline_instance
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('bot.pipeline_factory.GoogleSTTService')
    @patch('bot.pipeline_factory.OpenAILLMService')
    @patch('bot.pipeline_factory.GoogleTTSService')
    @patch('bot.pipeline_factory.Pipeline')
    async def test_pipeline_with_default_environment_config(
        self, 
        mock_pipeline, 
        mock_tts, 
        mock_llm, 
        mock_stt
    ):
        """Test pipeline creation with default environment configuration"""
        # Setup mocks
        mock_stt_instance = MagicMock()
        mock_llm_instance = MagicMock()
        mock_tts_instance = MagicMock()
        mock_pipeline_instance = MagicMock()
        
        mock_stt.return_value = mock_stt_instance
        mock_llm.return_value = mock_llm_instance
        mock_tts.return_value = mock_tts_instance
        mock_pipeline.return_value = mock_pipeline_instance
        
        # Minimal environment configuration
        minimal_env = {
            'GOOGLE_API_KEY': 'test-google-key',
            'OPENAI_API_KEY': 'test-openai-key'
        }
        
        config = TransportConfig(
            transport_type=TransportType.WEBSOCKET,
            sample_rate=24000
        )
        
        mock_transport = MagicMock()
        mock_transport.input.return_value = MagicMock()
        mock_transport.output.return_value = MagicMock()
        
        mock_context = MagicMock(spec=OpenAILLMContext)
        mock_context.get_messages.return_value = []
        mock_context.add_message.return_value = None
        mock_context.set_messages.return_value = None
        
        with patch.dict('os.environ', minimal_env, clear=True):
            pipeline = await create_pipeline(mock_transport, mock_context, config)
        
        # Verify services were created with default configuration
        mock_stt.assert_called_once_with(
            api_key='test-google-key',
            language='en-US',  # Default
            model='latest_long'  # Default
        )
        
        mock_llm.assert_called_once_with(
            api_key='test-openai-key',
            model='gpt-3.5-turbo'  # Default
        )
        
        mock_tts.assert_called_once_with(
            api_key='test-google-key',
            voice_id='en-US-Standard-A',  # Default
            sample_rate=24000
        )
        
        assert pipeline == mock_pipeline_instance
