"""
Configuration management for Voice Agent Server
Centralizes all configuration settings with environment variable support
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

class ServerConfig:
    """Server configuration with environment variable support"""
    
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "7860"))
    
    # Connection management
    MAX_CONNECTIONS: int = int(os.getenv("MAX_CONNECTIONS", "25"))
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "300"))  # 5 minutes
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "300"))  # 5 minutes
    
    # WebSocket settings
    WS_MAX_SIZE: int = int(os.getenv("WS_MAX_SIZE", str(16 * 1024 * 1024)))  # 16MB
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "20"))  # seconds
    WS_PING_TIMEOUT: int = int(os.getenv("WS_PING_TIMEOUT", "10"))  # seconds
    
    # Performance settings
    KEEP_ALIVE_TIMEOUT: int = int(os.getenv("KEEP_ALIVE_TIMEOUT", "30"))
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "60"))  # seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ACCESS_LOG: bool = os.getenv("ACCESS_LOG", "false").lower() == "true"
    
    # Server mode
    WEBSOCKET_SERVER: str = os.getenv("WEBSOCKET_SERVER", "fast_api")
    
    # API Keys (required)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # OpenAI settings
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "150"))
    
    # Google STT settings
    GOOGLE_STT_LANGUAGE: str = os.getenv("GOOGLE_STT_LANGUAGE", "en-US")
    GOOGLE_STT_MODEL: str = os.getenv("GOOGLE_STT_MODEL", "latest_long")
    GOOGLE_STT_ENABLE_INTERIM: bool = os.getenv("GOOGLE_STT_ENABLE_INTERIM", "true").lower() == "true"
    
    # Google TTS settings
    GOOGLE_TTS_VOICE: str = os.getenv("GOOGLE_TTS_VOICE", "en-US-Chirp3-HD-Laomedeia")
    GOOGLE_TTS_SAMPLE_RATE: int = int(os.getenv("GOOGLE_TTS_SAMPLE_RATE", "24000"))
    
    # Audio settings
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "24000"))
    CHANNELS: int = int(os.getenv("CHANNELS", "1"))
    
    # Pipeline settings
    ENABLE_INTERRUPTIONS: bool = os.getenv("ENABLE_INTERRUPTIONS", "true").lower() == "true"
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    
    # VAD settings
    VAD_STOP_SECS: float = float(os.getenv("VAD_STOP_SECS", "0.5"))
    VAD_START_SECS: float = float(os.getenv("VAD_START_SECS", "0.2"))
    VAD_MIN_VOLUME: float = float(os.getenv("VAD_MIN_VOLUME", "0.6"))
    
    @classmethod
    def validate(cls) -> tuple[bool, list[str]]:
        """Validate configuration and return status and missing keys"""
        required_keys = [
            "OPENAI_API_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        return len(missing_keys) == 0, missing_keys
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for the AI assistant"""
        return """You are a helpful AI voice assistant. Keep your responses:
- Conversational and natural
- Concise but informative (1-2 sentences typically)
- Friendly and engaging
- Appropriate for voice interaction

You can help with questions, provide information, have conversations, and assist with various tasks. Remember this is a voice conversation, so avoid long paragraphs or complex formatting."""
    
    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get configuration as dictionary for logging/debugging"""
        return {
            "server": {
                "host": cls.HOST,
                "port": cls.PORT,
                "max_connections": cls.MAX_CONNECTIONS,
                "connection_timeout": cls.CONNECTION_TIMEOUT,
                "websocket_server": cls.WEBSOCKET_SERVER
            },
            "websocket": {
                "max_size": cls.WS_MAX_SIZE,
                "ping_interval": cls.WS_PING_INTERVAL,
                "ping_timeout": cls.WS_PING_TIMEOUT
            },
            "performance": {
                "keep_alive_timeout": cls.KEEP_ALIVE_TIMEOUT,
                "cleanup_interval": cls.CLEANUP_INTERVAL,
                "enable_metrics": cls.ENABLE_METRICS
            },
            "ai_services": {
                "openai_model": cls.OPENAI_MODEL,
                "openai_temperature": cls.OPENAI_TEMPERATURE,
                "google_stt_model": cls.GOOGLE_STT_MODEL,
                "google_tts_voice": cls.GOOGLE_TTS_VOICE,
                "enable_streaming": cls.ENABLE_STREAMING,
                "enable_interruptions": cls.ENABLE_INTERRUPTIONS
            },
            "audio": {
                "sample_rate": cls.SAMPLE_RATE,
                "channels": cls.CHANNELS,
                "vad_stop_secs": cls.VAD_STOP_SECS,
                "vad_start_secs": cls.VAD_START_SECS
            }
        }
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)"""
        config = cls.get_config_dict()
        print("\n=== Server Configuration ===")
        for section, settings in config.items():
            print(f"\n{section.upper()}:")
            for key, value in settings.items():
                print(f"  {key}: {value}")
        print("\n" + "=" * 30)

# Global config instance
config = ServerConfig()

# Validate configuration on import
is_valid, missing_keys = config.validate()
if not is_valid:
    print(f"\n❌ Configuration validation failed!")
    print(f"Missing required environment variables: {', '.join(missing_keys)}")
    print("\nPlease set these in your .env file:")
    for key in missing_keys:
        print(f"  {key}=your_key_here")
    print("\nServer will not start until these are provided.\n")
else:
    print("✅ Configuration validation passed")
