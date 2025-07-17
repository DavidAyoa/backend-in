#!/usr/bin/env python3
"""
Unit tests for service pool
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from core.service_pool import ServicePool, ServicePoolConfig
from pipecat.transcriptions.language import Language


class TestServicePoolConfig:
    """Test service pool configuration"""
    
    @pytest.mark.unit
    def test_from_env_defaults(self):
        """Test creating config from environment with defaults"""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_APPLICATION_CREDENTIALS': 'test-creds'
        }):
            config = ServicePoolConfig.from_env()
            
            assert config.openai_api_key == 'test-key'
            assert config.openai_model == 'gpt-4o-mini'
            assert config.google_credentials_path == 'test-creds'
            assert config.google_stt_language == Language.EN_US
            assert config.pool_size == 5
    
    @pytest.mark.unit
    def test_from_env_custom_values(self):
        """Test creating config from environment with custom values"""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'custom-key',
            'OPENAI_MODEL': 'gpt-3.5-turbo',
            'GOOGLE_STT_LANGUAGE': 'fr-FR',
            'SERVICE_POOL_SIZE': '10'
        }):
            config = ServicePoolConfig.from_env()
            
            assert config.openai_api_key == 'custom-key'
            assert config.openai_model == 'gpt-3.5-turbo'
            assert config.google_stt_language == Language('fr-FR')
            assert config.pool_size == 10


class TestServicePool:
    """Test service pool functionality"""
    
    @pytest.fixture
    def service_config(self):
        """Create a test service pool config"""
        return ServicePoolConfig(
            openai_api_key='test-openai-key',
            google_credentials='test-google-creds',
            pool_size=2
        )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_pool_initialization(self, service_config):
        """Test service pool initialization"""
        pool = ServicePool(service_config)
        assert pool.config == service_config
        assert not pool._initialized
        assert pool._stt_count == 0
        assert pool._llm_count == 0
        assert pool._tts_count == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_pool_stats(self, service_config):
        """Test getting service pool statistics"""
        pool = ServicePool(service_config)
        stats = await pool.get_stats()
        
        assert 'stt_services' in stats
        assert 'llm_services' in stats
        assert 'tts_services' in stats
        assert stats['stt_services']['total_created'] == 0
        assert stats['stt_services']['available'] == 0
        assert stats['stt_services']['max_pool_size'] == 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_pool_cleanup(self, service_config):
        """Test service pool cleanup"""
        pool = ServicePool(service_config)
        await pool.cleanup()
        
        assert not pool._initialized
        assert pool._stt_services.empty()
        assert pool._llm_services.empty()
        assert pool._tts_services.empty()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_creation_mock(self, service_config):
        """Test service creation with mocked dependencies"""
        with patch('core.service_pool.GoogleSTTService') as mock_stt, \
             patch('core.service_pool.OpenAILLMService') as mock_llm, \
             patch('core.service_pool.GoogleTTSService') as mock_tts:
            
            # Setup mocks
            mock_stt.return_value = MagicMock()
            mock_llm.return_value = MagicMock()
            mock_tts.return_value = MagicMock()
            
            pool = ServicePool(service_config)
            
            # Test STT service creation
            stt_service = await pool._create_stt_service()
            assert stt_service is not None
            assert pool._stt_count == 1
            
            # Test LLM service creation
            llm_service = await pool._create_llm_service()
            assert llm_service is not None
            assert pool._llm_count == 1
            
            # Test TTS service creation
            tts_service = await pool._create_tts_service()
            assert tts_service is not None
            assert pool._tts_count == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_pool_return_services(self, service_config):
        """Test returning services to pool"""
        pool = ServicePool(service_config)
        
        # Mock services
        mock_stt = MagicMock()
        mock_llm = MagicMock()
        mock_tts = MagicMock()
        
        # Return services to pool
        await pool.return_stt_service(mock_stt)
        await pool.return_llm_service(mock_llm)
        await pool.return_tts_service(mock_tts)
        
        # Check that services were queued
        assert pool._stt_services.qsize() == 1
        assert pool._llm_services.qsize() == 1
        assert pool._tts_services.qsize() == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_pool_disable_reuse(self, service_config):
        """Test disabling service reuse"""
        service_config.enable_service_reuse = False
        pool = ServicePool(service_config)
        
        # Mock services
        mock_stt = MagicMock()
        
        # Return service to pool (should not be queued)
        await pool.return_stt_service(mock_stt)
        
        # Check that service was not queued
        assert pool._stt_services.qsize() == 0
