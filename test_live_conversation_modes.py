#!/usr/bin/env python3
"""
Live test for conversation modes against running server
Tests actual audio and text processing with real WebSocket connections
"""

import asyncio
import websockets
import json
import base64
import numpy as np
import time
from typing import Dict, Any, Optional
import requests

class LiveConversationTester:
    """Test conversation modes against live server"""
    
    def __init__(self, server_port=7860):
        self.server_port = server_port
        self.base_url = f"http://localhost:{server_port}"
        self.ws_url = f"ws://localhost:{server_port}/ws/flexible"
        
    def generate_test_audio(self, duration=1.0, sample_rate=16000, frequency=440):
        """Generate test audio data (sine wave)"""
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        # Generate sine wave
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3
        # Convert to 16-bit PCM
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        return audio_bytes
    
    def encode_audio_for_websocket(self, audio_bytes):
        """Encode audio data for WebSocket transmission"""
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    async def test_server_health(self):
        """Test if server is running and healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            print(f"✅ Server health check: {response.status_code}")
            if response.status_code == 200:
                print(f"   Server status: {response.json()}")
                return True
            return False
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            return False
    
    async def test_voice_to_voice_mode(self):
        """Test voice input to voice output mode"""
        print("\n🎤 Testing Voice-to-Voice Mode")
        
        try:
            # Generate test audio (2-second 440Hz tone)
            test_audio = self.generate_test_audio(duration=2.0, frequency=440)
            encoded_audio = self.encode_audio_for_websocket(test_audio)
            
            # Connect with voice-only mode
            uri = f"{self.ws_url}?voice_input=true&text_input=false&voice_output=true&text_output=false"
            
            async with websockets.connect(uri) as websocket:
                print("   ✅ WebSocket connected")
                
                # Send audio data
                audio_message = {
                    "type": "audio_input",
                    "data": encoded_audio,
                    "format": "pcm_16",
                    "sample_rate": 16000,
                    "channels": 1
                }
                
                await websocket.send(json.dumps(audio_message))
                print("   📤 Sent audio data")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    print(f"   📥 Received response: {response_data.get('type', 'unknown')}")
                    
                    if response_data.get('type') == 'audio_output':
                        print("   ✅ Voice-to-Voice mode working!")
                        return True
                    else:
                        print(f"   ⚠️  Unexpected response type: {response_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    print("   ⏰ Timeout waiting for response")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Voice-to-Voice test failed: {e}")
            return False
    
    async def test_text_to_text_mode(self):
        """Test text input to text output mode"""
        print("\n💬 Testing Text-to-Text Mode")
        
        try:
            # Connect with text-only mode
            uri = f"{self.ws_url}?voice_input=false&text_input=true&voice_output=false&text_output=true"
            
            async with websockets.connect(uri) as websocket:
                print("   ✅ WebSocket connected")
                
                # Send text message
                text_message = {
                    "type": "text_input",
                    "data": "Hello, this is a test message. Can you respond?"
                }
                
                await websocket.send(json.dumps(text_message))
                print("   📤 Sent text message")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    print(f"   📥 Received response: {response_data.get('type', 'unknown')}")
                    
                    if response_data.get('type') == 'text_output':
                        print(f"   💬 Response text: {response_data.get('data', '')[:100]}...")
                        print("   ✅ Text-to-Text mode working!")
                        return True
                    else:
                        print(f"   ⚠️  Unexpected response type: {response_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    print("   ⏰ Timeout waiting for response")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Text-to-Text test failed: {e}")
            return False
    
    async def test_voice_to_text_mode(self):
        """Test voice input to text output mode"""
        print("\n🎤➡️💬 Testing Voice-to-Text Mode")
        
        try:
            # Generate test audio
            test_audio = self.generate_test_audio(duration=1.5, frequency=800)
            encoded_audio = self.encode_audio_for_websocket(test_audio)
            
            # Connect with voice-to-text mode
            uri = f"{self.ws_url}?voice_input=true&text_input=false&voice_output=false&text_output=true"
            
            async with websockets.connect(uri) as websocket:
                print("   ✅ WebSocket connected")
                
                # Send audio data
                audio_message = {
                    "type": "audio_input",
                    "data": encoded_audio,
                    "format": "pcm_16",
                    "sample_rate": 16000,
                    "channels": 1
                }
                
                await websocket.send(json.dumps(audio_message))
                print("   📤 Sent audio data")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    print(f"   📥 Received response: {response_data.get('type', 'unknown')}")
                    
                    if response_data.get('type') == 'text_output':
                        print(f"   💬 Transcribed text: {response_data.get('data', '')[:100]}...")
                        print("   ✅ Voice-to-Text mode working!")
                        return True
                    else:
                        print(f"   ⚠️  Unexpected response type: {response_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    print("   ⏰ Timeout waiting for response")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Voice-to-Text test failed: {e}")
            return False
    
    async def test_text_to_voice_mode(self):
        """Test text input to voice output mode"""
        print("\n💬➡️🎤 Testing Text-to-Voice Mode")
        
        try:
            # Connect with text-to-voice mode
            uri = f"{self.ws_url}?voice_input=false&text_input=true&voice_output=true&text_output=false"
            
            async with websockets.connect(uri) as websocket:
                print("   ✅ WebSocket connected")
                
                # Send text message
                text_message = {
                    "type": "text_input",
                    "data": "Please convert this text to speech for testing purposes."
                }
                
                await websocket.send(json.dumps(text_message))
                print("   📤 Sent text message")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    print(f"   📥 Received response: {response_data.get('type', 'unknown')}")
                    
                    if response_data.get('type') == 'audio_output':
                        audio_size = len(response_data.get('data', ''))
                        print(f"   🎵 Audio response size: {audio_size} characters (base64)")
                        print("   ✅ Text-to-Voice mode working!")
                        return True
                    else:
                        print(f"   ⚠️  Unexpected response type: {response_data}")
                        return False
                        
                except asyncio.TimeoutError:
                    print("   ⏰ Timeout waiting for response")
                    return False
                    
        except Exception as e:
            print(f"   ❌ Text-to-Voice test failed: {e}")
            return False
    
    async def test_multimodal_mode(self):
        """Test full multimodal mode"""
        print("\n🌟 Testing Multimodal Mode (Voice+Text Input/Output)")
        
        try:
            # Generate test audio
            test_audio = self.generate_test_audio(duration=1.0, frequency=1000)
            encoded_audio = self.encode_audio_for_websocket(test_audio)
            
            # Connect with full multimodal mode
            uri = f"{self.ws_url}?voice_input=true&text_input=true&voice_output=true&text_output=true"
            
            async with websockets.connect(uri) as websocket:
                print("   ✅ WebSocket connected")
                
                # Send audio first
                audio_message = {
                    "type": "audio_input",
                    "data": encoded_audio,
                    "format": "pcm_16",
                    "sample_rate": 16000,
                    "channels": 1
                }
                
                await websocket.send(json.dumps(audio_message))
                print("   📤 Sent audio data")
                
                # Wait a bit, then send text
                await asyncio.sleep(1)
                
                text_message = {
                    "type": "text_input",
                    "data": "This is additional text input for multimodal testing."
                }
                
                await websocket.send(json.dumps(text_message))
                print("   📤 Sent text message")
                
                # Wait for responses
                responses_received = 0
                try:
                    while responses_received < 2:
                        response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                        response_data = json.loads(response)
                        response_type = response_data.get('type', 'unknown')
                        print(f"   📥 Received response {responses_received + 1}: {response_type}")
                        responses_received += 1
                        
                        if responses_received >= 2:
                            print("   ✅ Multimodal mode working!")
                            return True
                            
                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout - received {responses_received}/2 responses")
                    return responses_received > 0
                    
        except Exception as e:
            print(f"   ❌ Multimodal test failed: {e}")
            return False
    
    async def test_invalid_mode(self):
        """Test invalid mode configuration"""
        print("\n❌ Testing Invalid Mode Configuration")
        
        try:
            # Try to connect with invalid mode (no input or output)
            uri = f"{self.ws_url}?voice_input=false&text_input=false&voice_output=false&text_output=false"
            
            try:
                async with websockets.connect(uri) as websocket:
                    print("   ⚠️  Connection accepted (unexpected)")
                    return False
            except websockets.exceptions.ConnectionClosedError as e:
                print(f"   ✅ Connection properly rejected: {e.code}")
                return True
                
        except Exception as e:
            print(f"   ✅ Invalid mode properly handled: {e}")
            return True
    
    async def run_all_tests(self):
        """Run all conversation mode tests"""
        print("🚀 Starting Live Conversation Mode Tests")
        print(f"   Server: {self.base_url}")
        print(f"   WebSocket: {self.ws_url}")
        
        # Check server health first
        if not await self.test_server_health():
            print("❌ Server is not responding. Please ensure the server is running on port 7860")
            return
        
        # Run all tests
        tests = [
            ("Voice-to-Voice", self.test_voice_to_voice_mode),
            ("Text-to-Text", self.test_text_to_text_mode),
            ("Voice-to-Text", self.test_voice_to_text_mode),
            ("Text-to-Voice", self.test_text_to_voice_mode),
            ("Multimodal", self.test_multimodal_mode),
            ("Invalid Mode", self.test_invalid_mode),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
                await asyncio.sleep(1)  # Brief pause between tests
            except Exception as e:
                print(f"   ❌ {test_name} test crashed: {e}")
                results[test_name] = False
        
        # Print summary
        print("\n📊 Test Results Summary")
        print("=" * 40)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:20} | {status}")
            if result:
                passed += 1
        
        print("=" * 40)
        print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 All conversation modes are working correctly!")
        else:
            print("⚠️  Some conversation modes may need attention.")


async def main():
    """Main test runner"""
    tester = LiveConversationTester(server_port=7860)
    await tester.run_all_tests()


if __name__ == "__main__":
    # Install required packages if not available
    try:
        import numpy as np
        import websockets
        import requests
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install with: pip install numpy websockets requests")
        exit(1)
    
    # Run the tests
    asyncio.run(main())
