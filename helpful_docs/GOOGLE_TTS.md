Text-to-Speech

Google
======

Text-to-speech service using Google’s Cloud Text-to-Speech API

[​

](#overview)

Overview
----------------------------

Google Cloud Text-to-Speech provides high-quality speech synthesis with two implementations:

*   `GoogleTTSService`: Websocket-based streaming service
*   `GoogleHttpTTSService`: HTTP-based streaming service

`GoogleTTSService` offers the lowest latency and is the recommended option.

[

API Reference
-------------

Complete API documentation and method details







](https://reference-server.pipecat.ai/en/latest/api/pipecat.services.google.tts.html)[

Google Cloud TTS Docs
---------------------

Official Google Cloud Text-to-Speech documentation







](https://cloud.google.com/text-to-speech/docs)[

Example Code
------------

Working example with Chirp 3 HD voice







](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/07n-interruptible-google.py)

[​

](#installation)

Installation
------------------------------------

To use Google services, install the required dependencies:

Copy

Ask AI

    pip install "pipecat-ai[google]"
    

You’ll need to set up Google Cloud credentials through one of these methods:

*   Environment variable: `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON)
*   Service account JSON string
*   Service account file path

Create a service account in the [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts) with Text-to-Speech API permissions.

[​

](#frames)

Frames
------------------------

### 

[​

](#input)

Input

*   `TextFrame` - Text content to synthesize into speech
*   `TTSSpeakFrame` - Text that should be spoken immediately
*   `TTSUpdateSettingsFrame` - Runtime configuration updates
*   `LLMFullResponseStartFrame` / `LLMFullResponseEndFrame` - LLM response boundaries

### 

[​

](#output)

Output

*   `TTSStartedFrame` - Signals start of synthesis
*   `TTSAudioRawFrame` - Generated audio data (PCM format)
*   `TTSStoppedFrame` - Signals completion of synthesis
*   `ErrorFrame` - Google Cloud API or processing errors

[​

](#service-comparison)

Service Comparison
------------------------------------------------

Feature

GoogleTTSService (Streaming)

GoogleHttpTTSService (HTTP)

**Streaming**

✅ Real-time chunks

❌ Single audio block

**Latency**

🚀 Ultra-low

📈 Higher

**Voice Support**

Chirp 3 HD, Journey only

All Google voices

**SSML Support**

❌ Plain text only

✅ Full SSML

**Customization**

⚠️ Basic

✅ Extensive

[​

](#language-support)

Language Support
--------------------------------------------

View All Supported Languages

Language Code

Description

Service Code

`Language.AF`

Afrikaans

`af-ZA`

`Language.AR`

Arabic

`ar-XA`

`Language.BN`

Bengali

`bn-IN`

`Language.BG`

Bulgarian

`bg-BG`

`Language.CA`

Catalan

`ca-ES`

`Language.ZH`

Chinese (Mandarin)

`cmn-CN`

`Language.ZH_TW`

Chinese (Taiwan)

`cmn-TW`

`Language.ZH_HK`

Chinese (Hong Kong)

`yue-HK`

`Language.CS`

Czech

`cs-CZ`

`Language.DA`

Danish

`da-DK`

`Language.NL`

Dutch

`nl-NL`

`Language.NL_BE`

Dutch (Belgium)

`nl-BE`

`Language.EN`

English (US)

`en-US`

`Language.EN_AU`

English (Australia)

`en-AU`

`Language.EN_GB`

English (UK)

`en-GB`

`Language.EN_IN`

English (India)

`en-IN`

`Language.ET`

Estonian

`et-EE`

`Language.FIL`

Filipino

`fil-PH`

`Language.FI`

Finnish

`fi-FI`

`Language.FR`

French

`fr-FR`

`Language.FR_CA`

French (Canada)

`fr-CA`

`Language.GL`

Galician

`gl-ES`

`Language.DE`

German

`de-DE`

`Language.EL`

Greek

`el-GR`

`Language.GU`

Gujarati

`gu-IN`

`Language.HE`

Hebrew

`he-IL`

`Language.HI`

Hindi

`hi-IN`

`Language.HU`

Hungarian

`hu-HU`

`Language.IS`

Icelandic

`is-IS`

`Language.ID`

Indonesian

`id-ID`

`Language.IT`

Italian

`it-IT`

`Language.JA`

Japanese

`ja-JP`

`Language.KN`

Kannada

`kn-IN`

`Language.KO`

Korean

`ko-KR`

`Language.LV`

Latvian

`lv-LV`

`Language.LT`

Lithuanian

`lt-LT`

`Language.MS`

Malay

`ms-MY`

`Language.ML`

Malayalam

`ml-IN`

`Language.MR`

Marathi

`mr-IN`

`Language.NO`

Norwegian

`nb-NO`

`Language.PA`

Punjabi

`pa-IN`

`Language.PL`

Polish

`pl-PL`

`Language.PT`

Portuguese

`pt-PT`

`Language.PT_BR`

Portuguese (Brazil)

`pt-BR`

`Language.RO`

Romanian

`ro-RO`

`Language.RU`

Russian

`ru-RU`

`Language.SR`

Serbian

`sr-RS`

`Language.SK`

Slovak

`sk-SK`

`Language.ES`

Spanish

`es-ES`

`Language.ES_US`

Spanish (US)

`es-US`

`Language.SV`

Swedish

`sv-SE`

`Language.TA`

Tamil

`ta-IN`

`Language.TE`

Telugu

`te-IN`

`Language.TH`

Thai

`th-TH`

`Language.TR`

Turkish

`tr-TR`

`Language.UK`

Ukrainian

`uk-UA`

`Language.VI`

Vietnamese

`vi-VN`

Common languages supported include:

*   `Language.EN_US` - English (US)
*   `Language.EN_GB` - English (UK)
*   `Language.FR` - French
*   `Language.DE` - German
*   `Language.ES` - Spanish
*   `Language.IT` - Italian

[​

](#credential-setup)

Credential Setup
--------------------------------------------

### 

[​

](#environment-variable-method)

Environment Variable Method

Copy

Ask AI

    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
    

### 

[​

](#direct-credentials)

Direct Credentials

Copy

Ask AI

    # Using credentials string
    tts = GoogleTTSService(
        credentials='{"type": "service_account", "project_id": "...", ...}'
    )
    
    # Using credentials file path
    tts = GoogleTTSService(
        credentials_path="/path/to/service-account.json"
    )
    

[​

](#usage-example)

Usage Example
--------------------------------------

### 

[​

](#streaming-service-recommended-for-real-time)

Streaming Service (Recommended for Real-time)

Initialize `GoogleTTSService` and use it in a pipeline:

Copy

Ask AI

    from pipecat.services.google.tts import GoogleTTSService
    from pipecat.transcriptions.language import Language
    import os
    
    # Configure streaming service with Chirp 3 HD
    tts = GoogleTTSService(
        credentials=os.getenv("GOOGLE_TEST_CREDENTIALS"),
        voice_id="en-US-Chirp3-HD-Charon",
        params=GoogleTTSService.InputParams(
            language=Language.EN_US
        )
    )
    
    # Use in pipeline
    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant()
    ])
    

### 

[​

](#http-service-full-ssml-support)

HTTP Service (Full SSML Support)

Initialize `GoogleHttpTTSService` for more customization options:

Copy

Ask AI

    from pipecat.services.google.tts import GoogleHttpTTSService
    
    # Configure HTTP service with SSML customization
    http_tts = GoogleHttpTTSService(
        credentials_path="/path/to/service-account.json",
        voice_id="en-US-Neural2-A",
        params=GoogleHttpTTSService.InputParams(
            language=Language.EN_US,
            pitch="+2st",
            rate="1.2",
            volume="loud",
            emphasis="moderate",
            google_style="empathetic"
        )
    )
    

### 

[​

](#dynamic-configuration)

Dynamic Configuration

Make settings updates by pushing a `TTSUpdateSettingsFrame`:

Copy

Ask AI

    from pipecat.frames.frames import TTSUpdateSettingsFrame
    
    await task.queue_frame(TTSUpdateSettingsFrame(
        voice_id="new-voice-id",
      )
    )
    

[​

](#metrics)

Metrics
--------------------------

Both services provide comprehensive metrics:

*   **Time to First Byte (TTFB)** - Latency from text input to first audio
*   **Processing Duration** - Total synthesis time
*   **Character Usage** - Text processed for billing

[Learn how to enable Metrics](/guides/features/metrics) in your Pipeline.

[​

](#additional-notes)

Additional Notes
--------------------------------------------

*   **Voice Compatibility**: Streaming service only supports Chirp 3 HD and Journey voices
*   **SSML Limitations**: Chirp and Journey voices don’t support SSML - use plain text input
*   **Credential Management**: Supports multiple authentication methods for flexibility
*   **Regional Voices**: Match voice selection with language code for optimal results
*   **Streaming Advantage**: Use streaming service for conversational AI requiring ultra-low latency
*   **HTTP Advantage**: Use HTTP service when you need extensive voice customization via SSML

Assistant

Responses are generated using AI and may contain mistakes.

[Fish Audio](/server/services/tts/fish)[Groq](/server/services/tts/groq)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
