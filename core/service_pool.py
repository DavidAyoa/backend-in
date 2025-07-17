#!/usr/bin/env python3
"""
Service pool for managing shared Pipecat services
"""

import asyncio
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

import structlog
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.transcriptions.language import Language

logger = structlog.get_logger()


@dataclass
class ServicePoolConfig:
    """Configuration for the service pool"""
    # OpenAI configuration
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 150
    
    # Google configuration
    google_credentials: Optional[str] = None
    google_credentials_path: Optional[str] = None
    google_location: str = "global"
    
    # Google STT configuration
    google_stt_language: Language = Language.EN_US
    google_stt_model: str = "latest_long"
    google_stt_enable_interim: bool = True
    google_stt_enable_punctuation: bool = True
    
    # Google TTS configuration
    google_tts_voice: str = "en-US-Chirp3-HD-Charon"
    google_tts_language: Language = Language.EN_US
    google_tts_sample_rate: int = 24000
    
    # Pool configuration
    pool_size: int = 5
    enable_service_reuse: bool = True
    
    @classmethod
    def from_env(cls) -> 'ServicePoolConfig':
        """Create configuration from environment variables"""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "150")),
            
            google_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"),
            google_credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            google_location=os.getenv("GOOGLE_LOCATION", "global"),
            
            google_stt_language=Language(os.getenv("GOOGLE_STT_LANGUAGE", "en-US")),
            google_stt_model=os.getenv("GOOGLE_STT_MODEL", "latest_long"),
            google_stt_enable_interim=os.getenv("GOOGLE_STT_ENABLE_INTERIM", "true").lower() == "true",
            google_stt_enable_punctuation=os.getenv("GOOGLE_STT_ENABLE_PUNCTUATION", "true").lower() == "true",
            
            google_tts_voice=os.getenv("GOOGLE_TTS_VOICE", "en-US-Chirp3-HD-Charon"),
            google_tts_language=Language(os.getenv("GOOGLE_TTS_LANGUAGE", "en-US")),
            google_tts_sample_rate=int(os.getenv("GOOGLE_TTS_SAMPLE_RATE", "24000")),
            
            pool_size=int(os.getenv("SERVICE_POOL_SIZE", "5")),
            enable_service_reuse=os.getenv("ENABLE_SERVICE_REUSE", "true").lower() == "true",
        )


class ServicePool:
    """Pool of shared Pipecat services for efficient resource management"""
    
    def __init__(self, config: ServicePoolConfig):
        self.config = config
        self.logger = logger.bind(component="service_pool")
        
        # Service pools
        self._stt_services: asyncio.Queue = asyncio.Queue(maxsize=config.pool_size)
        self._llm_services: asyncio.Queue = asyncio.Queue(maxsize=config.pool_size)
        self._tts_services: asyncio.Queue = asyncio.Queue(maxsize=config.pool_size)
        
        # Service creation locks
        self._stt_lock = asyncio.Lock()
        self._llm_lock = asyncio.Lock()
        self._tts_lock = asyncio.Lock()
        
        # Service counts
        self._stt_count = 0
        self._llm_count = 0
        self._tts_count = 0
        
        # Initialization flag
        self._initialized = False
    
    async def initialize(self):
        """Initialize the service pool"""
        if self._initialized:
            return
        
        self.logger.info("Initializing service pool", pool_size=self.config.pool_size)
        
        # Pre-create initial services
        initial_services = min(2, self.config.pool_size)
        
        # Create initial STT services
        for _ in range(initial_services):
            stt_service = await self._create_stt_service()
            await self._stt_services.put(stt_service)
        
        # Create initial LLM services
        for _ in range(initial_services):
            llm_service = await self._create_llm_service()
            await self._llm_services.put(llm_service)
        
        # Create initial TTS services
        for _ in range(initial_services):
            tts_service = await self._create_tts_service()
            await self._tts_services.put(tts_service)
        
        self._initialized = True
        self.logger.info("Service pool initialized", initial_services=initial_services)
    
    async def get_stt_service(self) -> GoogleSTTService:
        """Get an STT service from the pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Try to get from pool first
            service = self._stt_services.get_nowait()
            return service
        except asyncio.QueueEmpty:
            # Create new service if pool is empty and we haven't reached limit
            async with self._stt_lock:
                if self._stt_count < self.config.pool_size:
                    service = await self._create_stt_service()
                    return service
                else:
                    # Wait for a service to become available
                    return await self._stt_services.get()
    
    async def get_llm_service(self) -> OpenAILLMService:
        """Get an LLM service from the pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            service = self._llm_services.get_nowait()
            return service
        except asyncio.QueueEmpty:
            async with self._llm_lock:
                if self._llm_count < self.config.pool_size:
                    service = await self._create_llm_service()
                    return service
                else:
                    return await self._llm_services.get()
    
    async def get_tts_service(self) -> GoogleTTSService:
        """Get a TTS service from the pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            service = self._tts_services.get_nowait()
            return service
        except asyncio.QueueEmpty:
            async with self._tts_lock:
                if self._tts_count < self.config.pool_size:
                    service = await self._create_tts_service()
                    return service
                else:
                    return await self._tts_services.get()
    
    async def return_stt_service(self, service: GoogleSTTService):
        """Return an STT service to the pool"""
        if self.config.enable_service_reuse:
            try:
                self._stt_services.put_nowait(service)
            except asyncio.QueueFull:
                # Pool is full, discard the service
                pass
    
    async def return_llm_service(self, service: OpenAILLMService):
        """Return an LLM service to the pool"""
        if self.config.enable_service_reuse:
            try:
                self._llm_services.put_nowait(service)
            except asyncio.QueueFull:
                pass
    
    async def return_tts_service(self, service: GoogleTTSService):
        """Return a TTS service to the pool"""
        if self.config.enable_service_reuse:
            try:
                self._tts_services.put_nowait(service)
            except asyncio.QueueFull:
                pass
    
    async def _create_stt_service(self) -> GoogleSTTService:
        """Create a new STT service"""
        # Prepare credentials
        credentials = None
        credentials_path = None
        
        if self.config.google_credentials:
            credentials = self.config.google_credentials
        elif self.config.google_credentials_path:
            credentials_path = self.config.google_credentials_path
        
        # Create service parameters
        params = GoogleSTTService.InputParams(
            languages=self.config.google_stt_language,
            model=self.config.google_stt_model,
            enable_automatic_punctuation=self.config.google_stt_enable_punctuation,
            enable_interim_results=self.config.google_stt_enable_interim,
        )
        
        service = GoogleSTTService(
            credentials=credentials,
            credentials_path=credentials_path,
            location=self.config.google_location,
            params=params
        )
        
        self._stt_count += 1
        self.logger.debug("Created STT service", total_count=self._stt_count)
        return service
    
    async def _create_llm_service(self) -> OpenAILLMService:
        """Create a new LLM service"""
        # Create service parameters
        params = OpenAILLMService.InputParams(
            temperature=self.config.openai_temperature,
            max_tokens=self.config.openai_max_tokens,
        )
        
        service = OpenAILLMService(
            model=self.config.openai_model,
            api_key=self.config.openai_api_key,
            params=params
        )
        
        self._llm_count += 1
        self.logger.debug("Created LLM service", total_count=self._llm_count)
        return service
    
    async def _create_tts_service(self) -> GoogleTTSService:
        """Create a new TTS service"""
        # Prepare credentials
        credentials = None
        credentials_path = None
        
        if self.config.google_credentials:
            credentials = self.config.google_credentials
        elif self.config.google_credentials_path:
            credentials_path = self.config.google_credentials_path
        
        # Create service parameters
        params = GoogleTTSService.InputParams(
            language=self.config.google_tts_language,
        )
        
        service = GoogleTTSService(
            credentials=credentials,
            credentials_path=credentials_path,
            voice_id=self.config.google_tts_voice,
            params=params
        )
        
        self._tts_count += 1
        self.logger.debug("Created TTS service", total_count=self._tts_count)
        return service
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get service pool statistics"""
        return {
            "stt_services": {
                "total_created": self._stt_count,
                "available": self._stt_services.qsize(),
                "max_pool_size": self.config.pool_size
            },
            "llm_services": {
                "total_created": self._llm_count,
                "available": self._llm_services.qsize(),
                "max_pool_size": self.config.pool_size
            },
            "tts_services": {
                "total_created": self._tts_count,
                "available": self._tts_services.qsize(),
                "max_pool_size": self.config.pool_size
            }
        }
    
    async def cleanup(self):
        """Clean up the service pool"""
        self.logger.info("Cleaning up service pool")
        
        # Clear all queues
        while not self._stt_services.empty():
            try:
                self._stt_services.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        while not self._llm_services.empty():
            try:
                self._llm_services.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        while not self._tts_services.empty():
            try:
                self._tts_services.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        self._initialized = False
        self.logger.info("Service pool cleaned up")


# Global service pool instance
_service_pool: Optional[ServicePool] = None


async def get_service_pool() -> ServicePool:
    """Get the global service pool instance"""
    global _service_pool
    
    if _service_pool is None:
        config = ServicePoolConfig.from_env()
        _service_pool = ServicePool(config)
        await _service_pool.initialize()
    
    return _service_pool


async def cleanup_service_pool():
    """Clean up the global service pool"""
    global _service_pool
    
    if _service_pool:
        await _service_pool.cleanup()
        _service_pool = None
