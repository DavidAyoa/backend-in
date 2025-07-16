"""
Configuration management for the Voice Agent Backend
Using Google STT/TTS and OpenAI LLM
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Server settings
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "8765"))
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # OpenAI Settings
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Google STT Settings
    GOOGLE_STT_LANGUAGE: str = os.getenv("GOOGLE_STT_LANGUAGE", "en-US")
    GOOGLE_STT_MODEL: str = os.getenv("GOOGLE_STT_MODEL", "latest_long")
    GOOGLE_STT_ENABLE_INTERIM: bool = os.getenv("GOOGLE_STT_ENABLE_INTERIM", "true").lower() == "true"
    
    # Google TTS Settings
    GOOGLE_TTS_VOICE: str = os.getenv("GOOGLE_TTS_VOICE", "en-US-Neural2-F")
    GOOGLE_TTS_SAMPLE_RATE: int = int(os.getenv("GOOGLE_TTS_SAMPLE_RATE", "24000"))
    
    # Audio Settings
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "24000"))
    CHANNELS: int = int(os.getenv("CHANNELS", "1"))
    
    # Pipeline Settings
    ENABLE_INTERRUPTIONS: bool = os.getenv("ENABLE_INTERRUPTIONS", "true").lower() == "true"
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "300"))  # 5 minutes
    ENABLE_STREAMING: bool = os.getenv("ENABLE_STREAMING", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        required_keys = [
            "OPENAI_API_KEY",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ]
        
        missing_keys = []
        for key in required_keys:
            if not getattr(cls, key):
                missing_keys.append(key)
        
        if missing_keys:
            print(f"Missing required environment variables: {', '.join(missing_keys)}")
            print("Please set these in your .env file:")
            for key in missing_keys:
                print(f"  {key}=your_key_here")
            return False
        
        return True
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for the AI assistant"""
        return """You are a helpful AI voice assistant. Keep your responses:
- Conversational and natural
- Concise but informative (1-2 sentences typically)
- Friendly and engaging
- Appropriate for voice interaction

You can help with questions, provide information, have conversations, and assist with various tasks. Remember this is a voice conversation, so avoid long paragraphs or complex formatting."""

# Global config instance
config = Config()
