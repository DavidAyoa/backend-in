Transport

SmallWebRTCTransport
====================

A lightweight WebRTC transport for peer-to-peer audio and video communication in Pipecat

Overview
----------------------------

`SmallWebRTCTransport` enables peer-to-peer WebRTC connections between clients and your Pipecat application. It implements bidirectional audio and video streaming using WebRTC for real-time communication.

This transport is intended for lightweight implementations, particularly for local development and testing. It expects your clients to include a corresponding `SmallWebRTCTransport` implementation. [See here](/client/js/transports/small-webrtc) for the JavaScript implementation.

`SmallWebRTCTransport` is best used for testing and development. For production deployments with scale, consider using the [DailyTransport](/server/services/transport/daily), as it has global, low-latency infrastructure.

Installation
------------------------------------

To use `SmallWebRTCTransport`, install the required dependencies:





    pip install pipecat-ai[webrtc]
    

(#class-reference)

Class Reference
------------------------------------------

### 

(#smallwebrtcconnection)

SmallWebRTCConnection

`SmallWebRTCConnection` manages the WebRTC connection details, peer connection state, and ICE candidates. It handles the signaling process and media tracks.





    SmallWebRTCConnection(ice_servers=None)
    

(#param-ice-servers)

ice\_servers

Union\[List\[str\], List\[IceServer\]\]

List of STUN/TURN server URLs for ICE connection establishment. Can be provided as strings or as IceServer objects.

#### 

(#methods)

Methods

(#param-initialize)

initialize

async method

Initialize the connection with a client’s SDP offer.

**Parameters:**

*   `sdp`: String containing the Session Description Protocol data from client’s offer
*   `type`: String representing the SDP message type (typically “offer”)





    await webrtc_connection.initialize(sdp=client_sdp, type="offer")
    

(#param-connect)

connect

async method

Establish the WebRTC peer connection after initialization.





    await webrtc_connection.connect()
    

(#param-close)

close

async method

Close the WebRTC peer connection.





    await webrtc_connection.close()
    

(#param-disconnect)

disconnect

async method

Disconnect the WebRTC peer connection and send a peer left message to the client.





    await webrtc_connection.disconnect()
    

(#param-renegotiate)

renegotiate

async method

Handle connection renegotiation requests.

**Parameters:**

*   `sdp`: String containing the Session Description Protocol data for renegotiation
*   `type`: String representing the SDP message type
*   `restart_pc`: Boolean indicating whether to completely restart the peer connection (default: False)





    await webrtc_connection.renegotiate(sdp=new_sdp, type="offer", restart_pc=False)
    

(#param-get-answer)

get\_answer

method

Retrieve the SDP answer to send back to the client.

Returns a dictionary with `sdp`, `type`, and `pc_id` fields.





    answer = webrtc_connection.get_answer()
    # Returns: {"sdp": "...", "type": "answer", "pc_id": "..."}
    

(#param-send-app-message)

send\_app\_message

method

Send an application message to the client.

**Parameters:**

*   `message`: The message to send (will be JSON serialized)





    webrtc_connection.send_app_message({"action": "greeting", "text": "Hello!"})
    

(#param-is-connected)

is\_connected

method

Check if the connection is active.





    if webrtc_connection.is_connected():
        print("Connection is active")
    

(#param-audio-input-track)

audio\_input\_track

method

Get the audio input track from the client.





    audio_track = webrtc_connection.audio_input_track()
    

(#param-video-input-track)

video\_input\_track

method

Get the video input track from the client.





    video_track = webrtc_connection.video_input_track()
    

(#param-replace-audio-track)

replace\_audio\_track

method

Replace the current audio track with a new one.

**Parameters:**

*   `track`: The new audio track to use





    webrtc_connection.replace_audio_track(new_audio_track)
    

(#param-replace-video-track)

replace\_video\_track

method

Replace the current video track with a new one.

**Parameters:**

*   `track`: The new video track to use





    webrtc_connection.replace_video_track(new_video_track)
    

(#param-ask-to-renegotiate)

ask\_to\_renegotiate

method

Request the client to initiate connection renegotiation.





    webrtc_connection.ask_to_renegotiate()
    

(#param-event-handler)

event\_handler

decorator

Register an event handler for connection events.

**Events:**

*   `"app-message"`: Called when a message is received from the client
*   `"track-started"`: Called when a new track is started
*   `"track-ended"`: Called when a track ends
*   `"connecting"`: Called when connection is being established
*   `"connected"`: Called when connection is established
*   `"disconnected"`: Called when connection is lost
*   `"closed"`: Called when connection is closed
*   `"failed"`: Called when connection fails
*   `"new"`: Called when a new connection is created





    @webrtc_connection.event_handler("connected")
    async def on_connected(connection):
        print(f"WebRTC connection established")
    

### 

(#smallwebrtctransport)

SmallWebRTCTransport

`SmallWebRTCTransport` is the main transport class that manages both input and output transports for WebRTC communication.





    SmallWebRTCTransport(
        webrtc_connection: SmallWebRTCConnection,
        params: TransportParams,
        input_name: Optional[str] = None,
        output_name: Optional[str] = None
    )
    

(#param-webrtc-connection)

webrtc\_connection

SmallWebRTCConnection

required

An instance of `SmallWebRTCConnection` that manages the WebRTC connection

(#param-params)

params

TransportParams

required

Configuration parameters for the transport

Show TransportParams properties

(#param-audio-in-enabled)

audio\_in\_enabled

bool

default:false

Enable audio input from the WebRTC client

(#param-audio-in-passthrough)

audio\_in\_passthrough

bool

default:"False"

When enabled, incoming audio frames are pushed downstream

(#param-audio-out-enabled)

audio\_out\_enabled

bool

default:false

Enable audio output to the WebRTC client

(#param-audio-in-sample-rate)

audio\_in\_sample\_rate

int

Sample rate for incoming audio (Hz)

(#param-audio-out-sample-rate)

audio\_out\_sample\_rate

int

Sample rate for outgoing audio (Hz)

(#param-audio-in-channels)

audio\_in\_channels

int

default:1

Number of audio input channels (1 for mono, 2 for stereo)

(#param-audio-out-channels)

audio\_out\_channels

int

default:1

Number of audio output channels (1 for mono, 2 for stereo)

(#param-video-in-enabled)

video\_in\_enabled

bool

default:false

Enable video input from the WebRTC client

(#param-video-out-enabled)

video\_out\_enabled

bool

default:false

Enable video output to the WebRTC client

(#param-video-out-width)

video\_out\_width

int

default:640

Width of outgoing video

(#param-video-out-height)

video\_out\_height

int

default:480

Height of outgoing video

(#param-video-out-framerate)

video\_out\_framerate

int

default:30

Framerate of outgoing video

(#param-vad-analyzer)

vad\_analyzer

VADAnalyzer

Custom VAD analyzer implementation

(#param-input-name)

input\_name

str

Optional name for the input transport

(#param-output-name)

output\_name

str

Optional name for the output transport

#### 

(#methods-2)

Methods

(#param-input)

input

method

Returns the input transport instance.





    input_transport = webrtc_transport.input()
    

(#param-output)

output

method

Returns the output transport instance.





    output_transport = webrtc_transport.output()
    

(#param-send-image)

send\_image

async method

Send an image frame to the client.

**Parameters:**

*   `frame`: The image frame to send (OutputImageRawFrame or SpriteFrame)





    await webrtc_transport.send_image(image_frame)
    

(#param-send-audio)

send\_audio

async method

Send an audio frame to the client.

**Parameters:**

*   `frame`: The audio frame to send (OutputAudioRawFrame)





    await webrtc_transport.send_audio(audio_frame)
    

#### 

(#event-handlers)

Event Handlers

(#param-on-app-message)

on\_app\_message

async callback

Called when receiving application messages from the client.

**Parameters:**

*   `message`: The received message





    @webrtc_transport.event_handler("on_app_message")
    async def on_app_message(message):
        print(f"Received message: {message}")
    

(#param-on-client-connected)

on\_client\_connected

async callback

Called when a client successfully connects.

**Parameters:**

*   `transport`: The SmallWebRTCTransport instance
*   `webrtc_connection`: The connection that was established





    @webrtc_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, webrtc_connection):
        print(f"Client connected")
    

(#param-on-client-disconnected)

on\_client\_disconnected

async callback

Called when a client disconnects.

**Parameters:**

*   `transport`: The SmallWebRTCTransport instance
*   `webrtc_connection`: The connection that was disconnected





    @webrtc_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, webrtc_connection):
        print(f"Client disconnected")
    

(#param-on-client-closed)

on\_client\_closed

async callback

Called when a client connection is closed.

**Parameters:**

*   `transport`: The SmallWebRTCTransport instance
*   `webrtc_connection`: The connection that was closed





    @webrtc_transport.event_handler("on_client_closed")
    async def on_client_closed(transport, webrtc_connection):
        print(f"Client connection closed")
    

(#basic-usage)

Basic Usage
----------------------------------

This basic usage example shows the transport specific parts of a bot.py file required to configure your bot:





    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
    from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection
    
    async def run_bot(webrtc_connection):
        # Create the WebRTC transport with the provided connection
        transport = SmallWebRTCTransport(
            webrtc_connection=webrtc_connection,
            params=TransportParams(
                audio_in_enabled=True,   # Accept audio from the client
                audio_out_enabled=True,  # Send audio to the client
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )
    
        # Set up your services and context
    
        # Create the pipeline
        pipeline = Pipeline([
            transport.input(),              # Receive audio from client
            stt,                            # Convert speech to text
            context_aggregator.user(),      # Add user messages to context
            llm,                            # Process text with LLM
            tts,                            # Convert text to speech
            transport.output(),             # Send audio responses to client
            context_aggregator.assistant(), # Add assistant responses to context
        ])
    
        # Register event handlers
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            logger.info("Client connected")
            # Start the conversation when client connects
            await task.queue_frames([context_aggregator.user().get_context_frame()])
    
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            logger.info("Client disconnected")
    
        @transport.event_handler("on_client_closed")
        async def on_client_closed(transport, client):
            logger.info("Client closed")
            await task.cancel()
    

(#how-to-connect-with-smallwebrtctransport)

How to connect with `SmallWebRTCTransport`
----------------------------------------------------------------------------------------------

For a client/server connection, you have two options for how to connect the client to the server:

1.  Use a Pipecat client SDK with the `SmallWebRTCTransport`. See the [Client SDK docs](/client/js/transports/small-webrtc) to get started.
2.  Using the WebRTC API directly. This is only recommended for advanced use cases where the Pipecat client SDKs don’t have an available transport.

(#examples)

Examples
----------------------------

To see a complete implementation, check out the following examples:

[

Video Transform
---------------

Demonstrates real-time video processing using WebRTC transport







](https://github.com/pipecat-ai/pipecat/tree/main/examples/p2p-webrtc/video-transform)[

Voice Agent
-----------

Implements a voice assistant using WebRTC for audio communication







](https://github.com/pipecat-ai/pipecat/tree/main/examples/p2p-webrtc/voice-agent)

(#media-handling)

Media Handling
----------------------------------------

### 

(#audio)

Audio

Audio is processed in 20ms chunks by default. The transport handles audio format conversion and resampling as needed:

*   Input audio is processed at 16kHz (mono) to be compatible with speech recognition services
*   Output audio can be configured to match your application’s requirements, but it must be mono, 16-bit PCM audio

### 

(#video)

Video

Video is streamed using RGB format by default. The transport provides:

*   Frame conversion between different color formats (RGB, YUV, etc.)
*   Configurable resolution and framerate

(#webrtc-ice-servers-configuration)

WebRTC ICE Servers Configuration
----------------------------------------------------------------------------

When implementing WebRTC in your project, **STUN** (Session Traversal Utilities for NAT) and **TURN** (Traversal Using Relays around NAT) servers are usually needed in cases where users are behind routers or firewalls.

In local networks (e.g., testing within the same home or office network), you usually don’t need to configure STUN or TURN servers. In such cases, WebRTC can often directly establish peer-to-peer connections without needing to traverse NAT or firewalls.

### 

(#what-are-stun-and-turn-servers%3F)

What are STUN and TURN Servers?

*   **STUN Server**: Helps clients discover their public IP address and port when they’re behind a NAT (Network Address Translation) device (like a router). This allows WebRTC to attempt direct peer-to-peer communication by providing the public-facing IP and port.
    
*   **TURN Server**: Used as a fallback when direct peer-to-peer communication isn’t possible due to strict NATs or firewalls blocking connections. The TURN server relays media traffic between peers.
    

### 

(#why-are-ice-servers-important%3F)

Why are ICE Servers Important?

**ICE (Interactive Connectivity Establishment)** is a framework used by WebRTC to handle network traversal and NAT issues. The `iceServers` configuration provides a list of **STUN** and **TURN** servers that WebRTC uses to find the best way to connect two peers.

(#advanced-configuration)

Advanced Configuration
--------------------------------------------------------

### 

(#ice-servers)

ICE Servers

For better connectivity, especially when testing across different networks, you can provide STUN servers:





    webrtc_connection = SmallWebRTCConnection(
        ice_servers=["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]
    )
    

You can also use IceServer objects for more advanced configuration:





    from pipecat.transports.network.webrtc_connection import IceServer
    
    webrtc_connection = SmallWebRTCConnection(
        ice_servers=[
            IceServer(urls="stun:stun.l.google.com:19302"),
            IceServer(
                urls="turn:turn.example.com:3478",
                username="username",
                credential="password"
            )
        ]
    )

Troubleshooting
------------------------------------------

If clients have trouble connecting or streaming:

1.  Check browser console for WebRTC errors
2.  Ensure you’re using HTTPS in production (required for WebRTC)
3.  For testing across networks, consider using Daily which provides TURN servers
4.  Verify browser permissions for camera and microphone

