Speech-to-Text

Google
======

Speech-to-text service implementation using Google Cloud’s Speech-to-Text V2 API

[​

](#overview)

Overview
----------------------------

`GoogleSTTService` provides real-time speech recognition using Google Cloud’s Speech-to-Text V2 API with support for 125+ languages, multiple models, voice activity detection, and advanced features like automatic punctuation and word-level confidence scores.

[

API Reference
-------------

Complete API documentation and method details







](https://reference-server.pipecat.ai/en/latest/api/pipecat.services.google.stt.html)[

Google Cloud Docs
-----------------

Official Google Cloud Speech-to-Text documentation







](https://cloud.google.com/speech-to-text/v2/docs)[

Example Code
------------

Working example with Google Cloud services







](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/07n-interruptible-google.py)

[​

](#installation)

Installation
------------------------------------

To use Google Cloud Speech services, install the required dependency:

Copy

Ask AI

    pip install "pipecat-ai[google]"
    

You’ll need Google Cloud credentials either as environment variables, a JSON string, or a service account file.

Get your credentials by creating a service account in the [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts) with Speech-to-Text API access.

[​

](#frames)

Frames
------------------------

### 

[​

](#input)

Input

*   `InputAudioRawFrame` - Raw PCM audio data (16-bit, configurable sample rate, mono)
*   `STTUpdateSettingsFrame` - Runtime transcription configuration updates
*   `STTMuteFrame` - Mute audio input for transcription

### 

[​

](#output)

Output

*   `InterimTranscriptionFrame` - Real-time transcription updates
*   `TranscriptionFrame` - Final transcription results with confidence scores
*   `ErrorFrame` - Connection or processing errors

[​

](#models)

Models
------------------------

Google Cloud offers specialized models for different use cases:

Model

Description

Best For

`latest_long`

Optimized for long-form speech

Conversations, meetings, podcasts

`chirp_2`

LLM powered ASR model

Streaming and multilingual

`telephony`

Optimized for phone call audio

Call centers, phone interviews

`medical_dictation`

Medical terminology optimized

Healthcare dictation

`medical_conversation`

Doctor-patient conversation optimized

Medical consultations

See [Google’s model documentation](https://cloud.google.com/speech-to-text/docs/transcription-model) for detailed performance comparisons.

[​

](#regional-support)

Regional Support
--------------------------------------------

Google Cloud Speech-to-Text V2 supports different regional endpoints:

Region

Description

Best For

`global`

Default global endpoint

General use, auto-routing

`us-central1`

US Central region

North American users

`europe-west1`

Europe West region

European users

`asia-northeast1`

Asia Northeast region

Asian users

Configure region for improved latency and data residency:

Copy

Ask AI

    stt = GoogleSTTService(
        location="us-central1",  # Regional endpoint
        credentials_path="credentials.json"
    )
    

[​

](#language-support)

Language Support
--------------------------------------------

Google Cloud STT supports 125+ languages with regional variants:

View All Supported Languages

Language Code

Description

Service Codes

`Language.AF`

Afrikaans

`af-ZA`

`Language.SQ`

Albanian

`sq-AL`

`Language.AM`

Amharic

`am-ET`

`Language.AR`

Arabic (Egypt)

`ar-EG`

`Language.AR_AE`

Arabic (UAE)

`ar-AE`

`Language.AR_SA`

Arabic (Saudi Arabia)

`ar-SA`

`Language.HY`

Armenian

`hy-AM`

`Language.AZ`

Azerbaijani

`az-AZ`

`Language.EU`

Basque

`eu-ES`

`Language.BN`

Bengali (India)

`bn-IN`

`Language.BN_BD`

Bengali (Bangladesh)

`bn-BD`

`Language.BS`

Bosnian

`bs-BA`

`Language.BG`

Bulgarian

`bg-BG`

`Language.MY`

Burmese

`my-MM`

`Language.CA`

Catalan

`ca-ES`

`Language.ZH`

Chinese (Simplified)

`cmn-Hans-CN`

`Language.ZH_TW`

Chinese (Traditional)

`cmn-Hant-TW`

`Language.YUE`

Chinese (Cantonese)

`yue-Hant-HK`

`Language.HR`

Croatian

`hr-HR`

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

`Language.EN_CA`

English (Canada)

`en-CA`

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

`Language.KA`

Georgian

`ka-GE`

`Language.DE`

German

`de-DE`

`Language.DE_AT`

German (Austria)

`de-AT`

`Language.EL`

Greek

`el-GR`

`Language.GU`

Gujarati

`gu-IN`

`Language.HE`

Hebrew

`iw-IL`

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

`Language.JV`

Javanese

`jv-ID`

`Language.KN`

Kannada

`kn-IN`

`Language.KK`

Kazakh

`kk-KZ`

`Language.KM`

Khmer

`km-KH`

`Language.KO`

Korean

`ko-KR`

`Language.LO`

Lao

`lo-LA`

`Language.LV`

Latvian

`lv-LV`

`Language.LT`

Lithuanian

`lt-LT`

`Language.MK`

Macedonian

`mk-MK`

`Language.MS`

Malay

`ms-MY`

`Language.ML`

Malayalam

`ml-IN`

`Language.MR`

Marathi

`mr-IN`

`Language.MN`

Mongolian

`mn-MN`

`Language.NE`

Nepali

`ne-NP`

`Language.NO`

Norwegian

`no-NO`

`Language.FA`

Persian

`fa-IR`

`Language.PL`

Polish

`pl-PL`

`Language.PT`

Portuguese

`pt-PT`

`Language.PT_BR`

Portuguese (Brazil)

`pt-BR`

`Language.PA`

Punjabi

`pa-Guru-IN`

`Language.RO`

Romanian

`ro-RO`

`Language.RU`

Russian

`ru-RU`

`Language.SR`

Serbian

`sr-RS`

`Language.SI`

Sinhala

`si-LK`

`Language.SK`

Slovak

`sk-SK`

`Language.SL`

Slovenian

`sl-SI`

`Language.ES`

Spanish (Spain)

`es-ES`

`Language.ES_MX`

Spanish (Mexico)

`es-MX`

`Language.ES_US`

Spanish (US)

`es-US`

`Language.SU`

Sundanese

`su-ID`

`Language.SW`

Swahili

`sw-TZ`

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

`Language.UR`

Urdu

`ur-IN`

`Language.UZ`

Uzbek

`uz-UZ`

`Language.VI`

Vietnamese

`vi-VN`

`Language.XH`

Xhosa

`xh-ZA`

`Language.ZU`

Zulu

`zu-ZA`

Common languages:

*   `Language.EN_US` - English (US) - `en-US`
*   `Language.ES` - Spanish - `es-ES`
*   `Language.FR` - French - `fr-FR`
*   `Language.DE` - German - `de-DE`
*   `Language.ZH` - Chinese (Simplified) - `cmn-Hans-CN`
*   `Language.JA` - Japanese - `ja-JP`

[​

](#usage-example)

Usage Example
--------------------------------------

### 

[​

](#basic-configuration)

Basic Configuration

Initialize the `GoogleSTTService` and use it in a pipeline:

Copy

Ask AI

    from pipecat.services.google.stt import GoogleSTTService
    from pipecat.transcriptions.language import Language
    
    # Using environment credentials
    stt = GoogleSTTService(
        params=GoogleSTTService.InputParams(
            languages=Language.EN_US,
            model="latest_long",
            enable_automatic_punctuation=True,
            enable_interim_results=True
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

](#credentials-configuration)

Credentials Configuration

Copy

Ask AI

    # Using service account file
    stt = GoogleSTTService(
        credentials_path="path/to/service-account.json",
        location="us-central1",
        params=GoogleSTTService.InputParams(languages=Language.EN_US)
    )
    
    # Using credentials JSON string
    stt = GoogleSTTService(
        credentials=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        params=GoogleSTTService.InputParams(languages=Language.EN_US)
    )
    

### 

[​

](#multi-language-configuration)

Multi-language Configuration

Copy

Ask AI

    # Multiple languages (first is primary)
    params = GoogleSTTService.InputParams(
        languages=[Language.EN_US, Language.ES_MX, Language.FR],
        model="latest_long",
        enable_automatic_punctuation=True
    )
    
    stt = GoogleSTTService(
        credentials_path="credentials.json",
        params=params
    )
    

### 

[​

](#dynamic-configuration-updates)

Dynamic Configuration Updates

Make settings updates by pushing an `STTUpdateSettingsFrame` for the `GoogleSTTService`:

Copy

Ask AI

    from pipecat.frames.frames import STTUpdateSettingsFrame
    
    await stt.update_options(
        languages=[Language.FR, Language.EN_US],
    )
    

[​

](#advanced-features)

Advanced Features
----------------------------------------------

### 

[​

](#multi-language-support)

Multi-language Support

*   Support for multiple languages simultaneously
*   First language in list is considered primary
*   Automatic language detection within configured set

### 

[​

](#voice-activity-detection)

Voice Activity Detection

*   Built-in VAD events from Google’s service
*   Integrates with Pipecat’s VAD framework
*   Configurable sensitivity and detection

### 

[​

](#content-processing)

Content Processing

*   **Automatic Punctuation**: Smart punctuation insertion
*   **Profanity Filtering**: Optional content filtering
*   **Format Control**: Handle spoken vs written formats

[​

](#metrics)

Metrics
--------------------------

The service provides comprehensive metrics:

*   **Time to First Byte (TTFB)** - Latency from audio input to first transcription
*   **Processing Duration** - Total time spent processing audio

[Learn how to enable Metrics](/guides/features/metrics) in your Pipeline.

Assistant

Responses are generated using AI and may contain mistakes.

[Gladia](/server/services/stt/gladia)[Groq (Whisper)](/server/services/stt/groq)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
