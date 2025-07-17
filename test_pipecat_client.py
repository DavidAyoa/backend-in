#!/usr/bin/env python3
"""
Pipecat Client Integration Test
Uses Pipecat's own WebSocket client transport for proper testing
"""

import asyncio
import requests
from urllib.parse import urlencode
from typing import Optional

from pipecat.frames.frames import (
    InputAudioRawFrame, 
    TextFrame, 
    TransportMessageFrame,
    TransportMessageUrgentFrame
)
from pipecat.transports.network.websocket_client import (
    WebsocketClientTransport,
    WebsocketClientParams,
    WebsocketClientCallbacks
)
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

import websockets
import json
import struct
import math

class TestFrameProcessor(FrameProcessor):
    """Simple processor to handle responses from the server"""
    
    def __init__(self):
        super().__init__()
        self.responses = []
    
    async def process_frame(self, frame, direction: FrameDirection):
        """Log received frames"""
        await super().process_frame(frame, direction)
        
        print(f"📨 Received frame: {type(frame).__name__}")
        if hasattr(frame, 'text') and frame.text:
            print(f"   Text: {frame.text}")
        elif hasattr(frame, 'message') and frame.message:
            print(f"   Message: {frame.message}")
        self.responses.append(frame)
        await self.push_frame(frame, direction)

async def test_websocket_client_connection(mode_params: dict, test_name: str) -> bool:
    """Test WebSocket connection with specific mode"""
    print(f"\n🧪 Testing {test_name}")
    
    # Build WebSocket URL
    ws_url = f"ws://localhost:7860/ws/flexible?{urlencode(mode_params)}"
    print(f"🔗 Connecting to: {ws_url}")
    
    try:
        # Create WebSocket client transport
        transport = WebsocketClientTransport(
            uri=ws_url,
            params=WebsocketClientParams(
                serializer=ProtobufFrameSerializer()
            )
        )
        
        # Set up event handlers
        connected_event = asyncio.Event()
        disconnected_event = asyncio.Event()
        
        @transport.event_handler("on_connected")
        async def on_connected(transport, websocket):
            print("✅ WebSocket connected")
            connected_event.set()
        
        @transport.event_handler("on_disconnected")
        async def on_disconnected(transport, websocket):
            print("🔌 WebSocket disconnected")
            disconnected_event.set()
        
        # Create test processor
        processor = TestFrameProcessor()
        
        # Create pipeline
        pipeline = Pipeline([
            transport.input(),
            processor,
            transport.output()
        ])
        
        # Create task and runner
        task = PipelineTask(pipeline, params=PipelineParams())
        runner = PipelineRunner()
        
        # Start the client pipeline in background
        client_task = asyncio.create_task(runner.run(task))
        
        # Wait for connection
        try:
            await asyncio.wait_for(connected_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            print("❌ Connection timeout")
            client_task.cancel()
            return False
        
        # Give pipeline time to fully initialize
        await asyncio.sleep(1)
        
        # Send test data based on mode
        if mode_params.get('text_input') == 'true':
            # Send text message
            text_frame = TextFrame(text="Hello, this is a test message from Pipecat client!")
            print(f"📤 Sending text frame: {text_frame.text}")
            await task.queue_frames([text_frame])
            
        elif mode_params.get('voice_input') == 'true':
            # Send audio data
            print("📤 Sending audio frame")
            
            # Generate simple sine wave (440Hz for 1 second)
            sample_rate = 16000
            duration = 1.0
            samples = int(sample_rate * duration)
            
            audio_data = []
            for i in range(samples):
                sample = int(16383 * math.sin(2 * math.pi * 440 * i / sample_rate))
                audio_data.extend(struct.pack('<h', sample))
            
            audio_frame = InputAudioRawFrame(
                audio=bytes(audio_data),
                sample_rate=sample_rate,
                num_channels=1
            )
            await task.queue_frames([audio_frame])
        
        # Wait for response
        print("⏳ Waiting for response...")
        response_timeout = 15.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < response_timeout:
            if processor.responses:
                print(f"✅ Received {len(processor.responses)} response(s)")
                for i, response in enumerate(processor.responses):
                    print(f"   Response {i+1}: {type(response).__name__}")
                return True
                
            await asyncio.sleep(0.1)
        
        print("⏰ No response received within timeout")
        return False
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    finally:
        if 'client_task' in locals():
            client_task.cancel()
            try:
                await client_task
            except asyncio.CancelledError:
                pass

async def test_simple_connection():
    """Test simple connection without full pipeline"""
    print("\n🔍 Testing Simple Connection")
    
    params = {
        'voice_input': 'true',
        'text_input': 'true', 
        'voice_output': 'true',
        'text_output': 'true'
    }
    
    ws_url = f"ws://localhost:7860/ws/flexible?{urlencode(params)}"
    
    try:
        async with websockets.connect(ws_url, open_timeout=10) as websocket:
            print("✅ Simple WebSocket connected")
            
            # Just wait and see if connection stays open
            await asyncio.sleep(3)
            
            if websocket.closed:
                print(f"❌ Connection closed: {websocket.close_code}")
                return False
            
            print("✅ Connection stable for 3 seconds")
            return True
            
    except Exception as e:
        print(f"❌ Simple connection error: {e}")
        return False

async def main():
    print("🚀 Pipecat Client Integration Tests")
    print("=" * 50)
    
    # Check server health
    try:
        response = requests.get("http://localhost:7860/health", timeout=5)
        print(f"✅ Server health: {response.status_code}")
        print(f"   Status: {response.json()}")
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return
    
    # Test cases
    test_cases = [
        # Simple connection test
        ("Simple Connection", test_simple_connection, {}),
        
        # Text-to-text mode
        ({
            'voice_input': 'false',
            'text_input': 'true',
            'voice_output': 'false', 
            'text_output': 'true'
        }, "Text-to-Text Mode"),
        
        # Voice-to-text mode
        ({
            'voice_input': 'true',
            'text_input': 'false',
            'voice_output': 'false',
            'text_output': 'true'
        }, "Voice-to-Text Mode"),
        
        # Voice-to-voice mode
        ({
            'voice_input': 'true',
            'text_input': 'false',
            'voice_output': 'true',
            'text_output': 'false'
        }, "Voice-to-Voice Mode"),
    ]
    
    results = []
    
    # Run simple connection test first
    simple_result = await test_simple_connection()
    results.append(("Simple Connection", simple_result))
    
    # Run Pipecat client tests
    for mode_params, test_name in test_cases[1:]:
        try:
            result = await test_websocket_client_connection(mode_params, test_name)
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 40)
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} | {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed ({passed/len(results)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
