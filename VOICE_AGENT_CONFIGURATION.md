# Voice Agent Configuration Guide

This document provides comprehensive information about configuring voice settings, Speech-to-Text (STT), Text-to-Speech (TTS), and Language Models (LLM) for your voice agents.

## 📋 Table of Contents

- [Overview](#overview)
- [Agent Voice Settings](#agent-voice-settings)
- [Speech-to-Text (STT) Configuration](#speech-to-text-stt-configuration)
- [Text-to-Speech (TTS) Configuration](#text-to-speech-tts-configuration)
- [Language Model (LLM) Configuration](#language-model-llm-configuration)
- [Environment Variables](#environment-variables)
- [API Examples](#api-examples)
- [Advanced Configuration](#advanced-configuration)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The voice agent system uses:
- **Google Cloud Speech-to-Text** for converting speech to text
- **Google Cloud Text-to-Speech** for converting text to speech
- **OpenAI GPT models** for language understanding and generation
- **Agent-specific voice settings** for customization per agent

## 🎤 Agent Voice Settings

### Voice Settings Structure

Each agent has a `voice_settings` field that stores configuration as JSON:

```json
{
  "voice_id": "en-US-Neural2-F",
  "language": "en-US",
  "sample_rate": 24000,
  "speed": 1.0,
  "pitch": 0.0,
  "volume_gain_db": 0.0,
  "effects": {
    "echo": false,
    "reverb": false
  },
  "stt_model": "latest_long",
  "llm_temperature": 0.7,
  "custom_prompt_additions": ""
}
```

### Supported Voice Settings Fields

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `voice_id` | string | Google TTS voice identifier | System default |
| `language` | string | Language code (e.g., "en-US", "es-ES") | "en-US" |
| `sample_rate` | integer | Audio sample rate in Hz | 24000 |
| `speed` | float | Speech speed multiplier (0.25-4.0) | 1.0 |
| `pitch` | float | Pitch adjustment in semitones (-20.0 to 20.0) | 0.0 |
| `volume_gain_db` | float | Volume gain in decibels (-96.0 to 16.0) | 0.0 |
| `stt_model` | string | STT model to use for this agent | System default |
| `llm_temperature` | float | LLM creativity level (0.0-2.0) | System default |
| `custom_prompt_additions` | string | Additional system prompt text | "" |

### Creating Agent with Voice Settings

```bash
curl -X POST http://localhost:8000/agents/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "Customer Support Bot",
    "description": "Helpful customer service assistant",
    "system_prompt": "You are a professional customer service representative.",
    "voice_settings": {
      "voice_id": "en-US-Neural2-F",
      "speed": 1.1,
      "pitch": -2.0,
      "stt_model": "latest_short",
      "llm_temperature": 0.5
    }
  }'
```

### Updating Agent Voice Settings

```bash
curl -X PUT http://localhost:8000/agents/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "voice_settings": {
      "voice_id": "en-US-Neural2-J",
      "speed": 0.9,
      "volume_gain_db": 3.0
    }
  }'
```

## 🎧 Speech-to-Text (STT) Configuration

### Google STT Models

| Model | Use Case | Latency | Accuracy |
|-------|----------|---------|----------|
| `latest_long` | Long-form audio, best accuracy | Higher | High |
| `latest_short` | Short queries, low latency | Lower | Good |
| `command_and_search` | Voice commands | Lowest | Good for commands |
| `phone_call` | Phone call audio | Medium | Optimized for telephony |
| `video` | Video/multimedia content | Medium | Good for video |

### STT Configuration Options

```python
# Global STT settings (environment variables)
GOOGLE_STT_LANGUAGE = "en-US"          # Language code
GOOGLE_STT_MODEL = "latest_long"       # Default model
GOOGLE_STT_ENABLE_INTERIM = True       # Enable interim results
```

### Supported Languages

| Language | Code | Description |
|----------|------|-------------|
| English (US) | en-US | US English |
| English (UK) | en-GB | British English |
| Spanish | es-ES | Spanish (Spain) |
| French | fr-FR | French (France) |
| German | de-DE | German (Germany) |
| Japanese | ja-JP | Japanese |
| Chinese | zh-CN | Chinese (Simplified) |
| Portuguese | pt-BR | Portuguese (Brazil) |

### Per-Agent STT Configuration

```json
{
  "voice_settings": {
    "stt_model": "latest_short",
    "language": "es-ES",
    "enable_interim": false
  }
}
```

## 🔊 Text-to-Speech (TTS) Configuration

### Google TTS Voices

#### English Voices

| Voice ID | Gender | Type | Description |
|----------|--------|------|-------------|
| `en-US-Neural2-A` | Male | Neural | Standard male voice |
| `en-US-Neural2-C` | Female | Neural | Standard female voice |
| `en-US-Neural2-D` | Male | Neural | Deep male voice |
| `en-US-Neural2-E` | Female | Neural | Young female voice |
| `en-US-Neural2-F` | Female | Neural | Warm female voice |
| `en-US-Neural2-G` | Female | Neural | Professional female voice |
| `en-US-Neural2-H` | Female | Neural | Confident female voice |
| `en-US-Neural2-I` | Male | Neural | Casual male voice |
| `en-US-Neural2-J` | Male | Neural | Professional male voice |
| `en-US-Chirp3-HD-Achernar` | Female | Chirp3 | High-quality female voice |

#### Studio Voices (Premium)

| Voice ID | Gender | Description |
|----------|--------|-------------|
| `en-US-Studio-M` | Male | Studio quality male |
| `en-US-Studio-O` | Female | Studio quality female |

#### Polyglot Voices (Multiple Languages)

| Voice ID | Languages | Description |
|----------|-----------|-------------|
| `en-US-Polyglot-1` | Multiple | Multilingual support |

### TTS Configuration Options

```python
# Global TTS settings
GOOGLE_TTS_VOICE = "en-US-Neural2-F"   # Default voice
GOOGLE_TTS_SAMPLE_RATE = 24000         # Sample rate (Hz)
```

### Voice Customization

```json
{
  "voice_settings": {
    "voice_id": "en-US-Neural2-F",
    "sample_rate": 24000,
    "speed": 1.0,
    "pitch": 0.0,
    "volume_gain_db": 0.0,
    "effects": {
      "echo": false,
      "reverb": false
    }
  }
}
```

## 🧠 Language Model (LLM) Configuration

### OpenAI Models

| Model | Context Length | Use Case | Cost |
|-------|----------------|----------|------|
| `gpt-3.5-turbo` | 4,096 tokens | General purpose | Low |
| `gpt-3.5-turbo-16k` | 16,384 tokens | Longer conversations | Medium |
| `gpt-4` | 8,192 tokens | High quality responses | High |
| `gpt-4-32k` | 32,768 tokens | Extended conversations | Highest |
| `gpt-4-turbo` | 128,000 tokens | Latest capabilities | High |

### LLM Configuration Options

```python
# Global LLM settings
OPENAI_MODEL = "gpt-3.5-turbo"         # Default model
OPENAI_TEMPERATURE = 0.7               # Creativity level
OPENAI_MAX_TOKENS = 150                # Response length limit
```

### Temperature Guidelines

| Temperature | Behavior | Use Case |
|-------------|----------|----------|
| 0.0 - 0.3 | Deterministic, focused | Technical support, factual Q&A |
| 0.4 - 0.7 | Balanced | General conversation |
| 0.8 - 1.0 | Creative | Creative writing, brainstorming |
| 1.1 - 2.0 | Very creative | Experimental, artistic |

### Per-Agent LLM Configuration

```json
{
  "voice_settings": {
    "llm_temperature": 0.3,
    "llm_model": "gpt-4",
    "max_tokens": 100,
    "custom_prompt_additions": "Always be concise and professional."
  }
}
```

## 🌐 Environment Variables

### Required Variables

```bash
# API Keys (Required)
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=path/to/google/credentials.json
```

### OpenAI Configuration

```bash
# OpenAI Settings
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=150
```

### Google STT Configuration

```bash
# Google STT Settings
GOOGLE_STT_LANGUAGE=en-US
GOOGLE_STT_MODEL=latest_long
GOOGLE_STT_ENABLE_INTERIM=true
```

### Google TTS Configuration

```bash
# Google TTS Settings
GOOGLE_TTS_VOICE=en-US-Neural2-F
GOOGLE_TTS_SAMPLE_RATE=24000
```

### Audio Settings

```bash
# Audio Configuration
SAMPLE_RATE=24000
CHANNELS=1
```

### Pipeline Settings

```bash
# Pipeline Configuration
ENABLE_INTERRUPTIONS=true
ENABLE_STREAMING=true
```

### VAD (Voice Activity Detection) Settings

```bash
# VAD Configuration
VAD_STOP_SECS=0.5      # Seconds of silence to stop recording
VAD_START_SECS=0.2     # Seconds to start recording
VAD_MIN_VOLUME=0.6     # Minimum volume threshold
```

## 📋 API Examples

### View Agent Configuration

```bash
# Get agent details including voice settings
curl -X GET http://localhost:8000/agents/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response:
```json
{
  "id": 1,
  "agent_name": "Customer Support Bot",
  "description": "Helpful customer service assistant",
  "system_prompt": "You are a professional customer service representative.",
  "voice_settings": {
    "voice_id": "en-US-Neural2-F",
    "speed": 1.1,
    "pitch": -2.0,
    "stt_model": "latest_short",
    "llm_temperature": 0.5
  },
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### List All Agents

```bash
# List all user agents
curl -X GET http://localhost:8000/agents/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Voice Settings Only

```bash
# Update only voice settings
curl -X PUT http://localhost:8000/agents/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "voice_settings": {
      "voice_id": "en-US-Neural2-J",
      "speed": 0.9,
      "volume_gain_db": 3.0,
      "llm_temperature": 0.8
    }
  }'
```

### Create Multi-Language Agent

```bash
# Create Spanish-speaking agent
curl -X POST http://localhost:8000/agents/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "Asistente en Español",
    "description": "Asistente de servicio al cliente en español",
    "system_prompt": "Eres un asistente de servicio al cliente profesional que habla español.",
    "voice_settings": {
      "voice_id": "es-ES-Neural2-A",
      "language": "es-ES",
      "stt_model": "latest_long",
      "llm_temperature": 0.6
    }
  }'
```

## ⚙️ Advanced Configuration

### Custom Voice Profiles

Create specialized voice profiles for different use cases:

```json
{
  "customer_service": {
    "voice_id": "en-US-Neural2-F",
    "speed": 1.0,
    "pitch": -1.0,
    "volume_gain_db": 2.0,
    "llm_temperature": 0.4
  },
  "technical_support": {
    "voice_id": "en-US-Neural2-J",
    "speed": 0.9,
    "pitch": 0.0,
    "volume_gain_db": 0.0,
    "llm_temperature": 0.2
  },
  "sales": {
    "voice_id": "en-US-Neural2-H",
    "speed": 1.1,
    "pitch": 2.0,
    "volume_gain_db": 1.0,
    "llm_temperature": 0.7
  }
}
```

### Dynamic Configuration

Update agent settings based on context:

```python
# Example: Adjust settings based on time of day
import datetime

def get_voice_settings_for_time():
    current_hour = datetime.datetime.now().hour
    
    if 9 <= current_hour <= 17:  # Business hours
        return {
            "voice_id": "en-US-Neural2-F",
            "speed": 1.0,
            "llm_temperature": 0.4
        }
    else:  # After hours
        return {
            "voice_id": "en-US-Neural2-C",
            "speed": 0.9,
            "llm_temperature": 0.6
        }
```

### Performance Optimization

```bash
# Low-latency configuration
GOOGLE_STT_MODEL=latest_short
GOOGLE_TTS_SAMPLE_RATE=16000
VAD_STOP_SECS=0.3
VAD_START_SECS=0.1
ENABLE_STREAMING=true
```

```bash
# High-quality configuration
GOOGLE_STT_MODEL=latest_long
GOOGLE_TTS_SAMPLE_RATE=48000
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.5
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Voice Not Working

**Symptoms:** Agent created but no voice output

**Solutions:**
- Check Google Cloud credentials
- Verify `GOOGLE_APPLICATION_CREDENTIALS` path
- Test with default voice settings
- Check TTS service quotas

```bash
# Test with minimal voice settings
{
  "voice_settings": {
    "voice_id": "en-US-Neural2-F"
  }
}
```

#### 2. STT Not Recognizing Speech

**Symptoms:** Speech not converted to text

**Solutions:**
- Check audio input format
- Verify language settings match spoken language
- Try different STT models
- Check microphone permissions

```bash
# Test with different STT model
{
  "voice_settings": {
    "stt_model": "latest_short",
    "language": "en-US"
  }
}
```

#### 3. Poor Voice Quality

**Symptoms:** Robotic or distorted voice

**Solutions:**
- Increase sample rate
- Adjust speed and pitch
- Try different voice models
- Check audio output settings

```bash
# High-quality voice settings
{
  "voice_settings": {
    "voice_id": "en-US-Neural2-F",
    "sample_rate": 48000,
    "speed": 1.0,
    "pitch": 0.0,
    "volume_gain_db": 0.0
  }
}
```

#### 4. High Latency

**Symptoms:** Slow response times

**Solutions:**
- Use `latest_short` STT model
- Reduce sample rate
- Adjust VAD settings
- Enable streaming

```bash
# Low-latency configuration
GOOGLE_STT_MODEL=latest_short
GOOGLE_TTS_SAMPLE_RATE=16000
VAD_STOP_SECS=0.2
ENABLE_STREAMING=true
```

### Debugging Commands

```bash
# Check agent configuration
curl -X GET http://localhost:8000/agents/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test voice settings
curl -X PUT http://localhost:8000/agents/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"voice_settings": {"voice_id": "en-US-Neural2-F"}}'

# Check server health
curl -X GET http://localhost:8000/health

# View server metrics
curl -X GET http://localhost:8000/metrics
```

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Voice not found` | Invalid voice_id | Use valid Google TTS voice ID |
| `Language not supported` | Invalid language code | Use supported language codes |
| `STT model not available` | Invalid STT model | Use supported STT models |
| `Invalid temperature` | Temperature out of range | Use 0.0-2.0 range |
| `Quota exceeded` | API limits reached | Check Google Cloud quotas |

## 📚 Additional Resources

### Documentation Links

- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text/docs)
- [Google Cloud Text-to-Speech](https://cloud.google.com/text-to-speech/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Pipecat Framework](https://docs.pipecat.ai/)

### Voice Samples

Test different voices at:
- [Google Cloud TTS Demo](https://cloud.google.com/text-to-speech)
- [Voice samples repository](https://github.com/googleapis/python-texttospeech/tree/main/samples)

### Community Resources

- [Voice Agent Discord](https://discord.gg/voiceagents)
- [GitHub Issues](https://github.com/your-repo/issues)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/voice-agents)

---

**Last Updated:** January 2024  
**Version:** 1.0.0  
**Author:** Voice Agent Team

For questions or issues, please refer to the troubleshooting section or contact support.
