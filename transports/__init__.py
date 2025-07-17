from .base import BaseTransportManager, TransportType
from .websocket.manager import WebSocketTransportManager
from .factory import TransportFactory

# Conditional import for WebRTC (requires optional dependencies)
try:
    from .webrtc.manager import WebRTCTransportManager
    _webrtc_available = True
except ImportError:
    _webrtc_available = False
    WebRTCTransportManager = None

__all__ = [
    "BaseTransportManager",
    "TransportType",
    "WebSocketTransportManager",
    "TransportFactory",
]

if _webrtc_available:
    __all__.append("WebRTCTransportManager")
