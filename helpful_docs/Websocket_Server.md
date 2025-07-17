Transport

WebSocket Server
================

WebSocket server transport implementation for real-time audio communication

[​

](#overview)

Overview
----------------------------

`WebsocketServerTransport` provides a WebSocket server implementation for real-time audio communication. It supports bidirectional audio streams and voice activity detection (VAD).

WebsocketServerTransport is best suited for server-side applications and prototyping client/server apps.

For client/server production applications, we strongly recommend using a WebRTC-based transport for robust network and media handling.

[​

](#installation)

Installation
------------------------------------

To use `WebsocketServerTransport`, install the required dependencies:

Copy

Ask AI

    pip install "pipecat-ai[websocket]"
    

[​

](#configuration)

Configuration
--------------------------------------

### 

[​

](#constructor-parameters)

Constructor Parameters

[​

](#param-host)

host

str

default:"localhost"

Host address to bind the WebSocket server

[​

](#param-port)

port

int

default:"8765"

Port number for the WebSocket server

[​

](#param-params)

params

WebsocketServerParams

default:"WebsocketServerParams()"

Transport configuration parameters

### 

[​

](#websocketserverparams-configuration)

WebsocketServerParams Configuration

[​

](#param-add-wav-header)

add\_wav\_header

bool

default:"False"

Add WAV header to audio frames

[​

](#param-serializer)

serializer

FrameSerializer

default:"ProtobufFrameSerializer()"

Frame serializer for WebSocket messages

[​

](#param-session-timeout)

session\_timeout

int | None

default:"None"

Session timeout in seconds. If set, triggers timeout event when no activity is detected

#### 

[​

](#audio-configuration)

Audio Configuration

[​

](#param-audio-in-enabled)

audio\_in\_enabled

bool

default:false

Enable audio input from the WebRTC client

[​

](#param-audio-in-passthrough)

audio\_in\_passthrough

bool

default:"False"

When enabled, incoming audio frames are pushed downstream

[​

](#param-audio-out-enabled)

audio\_out\_enabled

bool

default:"False"

Enable audio output capabilities

[​

](#param-audio-out-sample-rate)

audio\_out\_sample\_rate

int

default:"None"

Audio output sample rate in Hz

[​

](#param-audio-out-channels)

audio\_out\_channels

int

default:"1"

Number of audio output channels

#### 

[​

](#voice-activity-detection-vad)

Voice Activity Detection (VAD)

[​

](#param-vad-analyzer)

vad\_analyzer

VADAnalyzer | None

default:"None"

Voice Activity Detection analyzer. You can set this to either `SileroVADAnalyzer()` or `WebRTCVADAnalyzer()`. SileroVADAnalyzer is the recommended option. Learn more about the [SileroVADAnalyzer](/server/utilities/audio/silero-vad-analyzer).

[​

](#basic-usage)

Basic Usage
----------------------------------

Copy

Ask AI

    from pipecat.transports.network.websocket_server import (
        WebsocketServerTransport,
        WebsocketServerParams
    )
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.pipeline import Pipeline
    
    # Configure transport
    transport = WebsocketServerTransport(
        host="localhost",
        port=8765,
        params=WebsocketServerParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=True,
            vad_analyzer=SileroVADAnalyzer(),
            session_timeout=180  # 3 minutes
        )
    )
    
    # Use in pipeline
    pipeline = Pipeline([
        transport.input(),    # Handle incoming audio
        stt,          # Speech-to-text
        llm,          # Language model
        tts,          # Text-to-speech
        transport.output()    # Handle outgoing audio
    ])
    

Check out the [Websocket Server example](https://github.com/pipecat-ai/pipecat/tree/main/examples/websocket-server) to see how to use this transport in a pipeline.

[​

](#event-callbacks)

Event Callbacks
------------------------------------------

WebsocketServerTransport provides callbacks for handling client connection events. Register callbacks using the `@transport.event_handler()` decorator.

### 

[​

](#connection-events)

Connection Events

[​

](#param-on-client-connected)

on\_client\_connected

async callback

Called when a client connects to the WebSocket server.

**Parameters:**

*   `transport`: The WebsocketServerTransport instance
*   `client`: WebSocket client connection object

Copy

Ask AI

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected: {client.remote_address}")
        # Initialize conversation
        await task.queue_frames([LLMMessagesFrame(initial_messages)])
    

[​

](#param-on-client-disconnected)

on\_client\_disconnected

async callback

Called when a client disconnects from the WebSocket server.

**Parameters:**

*   `transport`: The WebsocketServerTransport instance
*   `client`: WebSocket client connection object

Copy

Ask AI

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected: {client.remote_address}")
    

[​

](#param-on-session-timeout)

on\_session\_timeout

async callback

Called when a session times out (if session\_timeout is configured).

**Parameters:**

*   `transport`: The WebsocketServerTransport instance
*   `client`: WebSocket client connection object

Copy

Ask AI

    @transport.event_handler("on_session_timeout")
    async def on_session_timeout(transport, client):
        logger.info(f"Session timeout for client: {client.remote_address}")
        # Handle timeout (e.g., send message, close connection)
    

[​

](#frame-types)

Frame Types
----------------------------------

### 

[​

](#input-frames)

Input Frames

[​

](#param-input-audio-raw-frame)

InputAudioRawFrame

Frame

Raw audio data from the WebSocket client

### 

[​

](#output-frames)

Output Frames

[​

](#param-output-audio-raw-frame)

OutputAudioRawFrame

Frame

Audio data to be sent to the WebSocket client

[​

](#notes)

Notes
----------------------

*   Supports real-time audio communication
*   Best suited for server-side applications
*   Handles WebSocket connection management
*   Provides voice activity detection
*   Supports session timeouts
*   Single client per server (new connections replace existing ones)
*   All callbacks are asynchronous

Assistant

Responses are generated using AI and may contain mistakes.

[FastAPI WebSocket](/server/services/transport/fastapi-websocket)[Frame Serializer Overview](/server/services/serializers/introduction)

[x](https://x.com/pipecat_ai)[github](https://github.com/pipecat-ai/pipecat)[discord](https://discord.gg/pipecat)

[Powered by Mintlify](https://mintlify.com/preview-request?utm_campaign=poweredBy&utm_medium=referral&utm_source=daily)
