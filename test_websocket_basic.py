#!/usr/bin/env python3
"""
Basic WebSocket Connection Test
Isolates WebSocket connection issues without pipeline complexity
"""

import asyncio
import json
import websockets
import requests
from urllib.parse import urlencode

async def test_basic_websocket_connection():
    """Test basic WebSocket connection without sending data"""
    
    # Check server health first
    try:
        response = requests.get("http://localhost:7860/health")
        print(f"✅ Server health: {response.status_code}")
        print(f"   Status: {response.json()}")
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        return False
    
    # Test basic WebSocket connection
    params = {
        'voice_input': 'true',
        'text_input': 'false', 
        'voice_output': 'true',
        'text_output': 'false'
    }
    
    ws_url = f"ws://localhost:7860/ws/flexible?{urlencode(params)}"
    print(f"🔗 Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully")
            
            # Wait a moment to see if connection stays open
            await asyncio.sleep(2)
            
            # Check if still connected
            if websocket.closed:
                print(f"❌ WebSocket closed unexpectedly: {websocket.close_code} - {websocket.close_reason}")
                return False
            
            print("✅ WebSocket connection stable for 2 seconds")
            
            # Try to receive any messages from server
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                print(f"📨 Received: {message}")
                return True
            except asyncio.TimeoutError:
                print("⏰ No immediate messages received (this is OK)")
                return True
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ WebSocket connection closed: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

async def test_multiple_connections():
    """Test multiple consecutive connections"""
    print("\n🔄 Testing multiple consecutive connections...")
    
    for i in range(3):
        print(f"\n--- Connection {i+1}/3 ---")
        success = await test_basic_websocket_connection()
        if not success:
            print(f"❌ Connection {i+1} failed")
            return False
        await asyncio.sleep(1)  # Small delay between connections
    
    print("✅ All connections successful")
    return True

async def main():
    print("🚀 Starting Basic WebSocket Connection Test")
    print("   Testing WebSocket connectivity without pipeline complexity")
    
    success = await test_basic_websocket_connection()
    if success:
        await test_multiple_connections()
    
    print("\n📊 Basic WebSocket Test Complete")

if __name__ == "__main__":
    asyncio.run(main())
