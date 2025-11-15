import sys
import os

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from peer.tunnel_handler import TunnelHandler

@pytest.fixture
def stun_server():
    return "stun:stun.l.google.com:19302"

@pytest.fixture
def tunnel_handler(stun_server):
    return TunnelHandler(stun_server=stun_server)

def test_webrtc_offer(tunnel_handler):
    """Test WebRTC offer handling (simplified mock)."""
    offer = {
        "sdp": "v=0\no=- 46117317 2 IN IP4 127.0.0.1\ns=-\nt=0 0\na=sendrecv",
        "type": "offer"
    }
    # Run the async function synchronously for testing
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    response = loop.run_until_complete(tunnel_handler.handle_offer(offer))
    loop.close()
    
    assert "sdp" in response
    assert "type" in response
    assert response["type"] == "answer"

class TestHTTPSTunnel(AioHTTPTestCase):
    """Test HTTPS tunnel functionality using WebSocket."""
    
    async def get_application(self):
        """Create application for testing."""
        app = web.Application()
        handler = TunnelHandler()
        app.router.add_get("/webrtc", handler.https_tunnel)
        return app

    async def test_https_tunnel(self):
        """Test WebSocket tunnel connection and message echo."""
        async with self.client.ws_connect("/webrtc") as ws:
            # Send a valid authenticated message (JSON)
            await ws.send_str('{"type": "rendezvous", "data": "test"}')
            msg = await ws.receive()
            assert msg.type == web.WSMsgType.TEXT
            assert "ok" in msg.data

            # Send an unauthenticated message (missing type)
            await ws.send_str('{"data": "test"}')
            msg = await ws.receive()
            assert msg.type == web.WSMsgType.TEXT
            assert "auth_failed" in msg.data

            # Test rate limiting (send >10 messages quickly)
            rate_limited = False
            for _ in range(12):
                await ws.send_str('{"type": "rendezvous", "data": "test"}')
                msg = await ws.receive()
                if "rate_limited" in msg.data:
                    rate_limited = True
            assert rate_limited

            # Test message batching with msgpack
            import msgpack
            batch = [
                {"type": "rendezvous", "data": "batch1"},
                {"type": "rendezvous", "data": "batch2"},
                {"data": "unauth"}
            ]
            await ws.send_bytes(msgpack.packb(batch))
            # Receive responses for each item in batch
            for _ in range(3):
                msg = await ws.receive()
                assert msg.type == web.WSMsgType.BINARY
                resp = msgpack.unpackb(msg.data, raw=False)
                assert resp["status"] in ["ok", "auth_failed", "rate_limited"]

    async def test_stream_multiplexing_and_compression(self):
        """Test stream multiplexing and compression in TunnelHandler."""
        import msgpack, zlib
        async with self.client.ws_connect("/webrtc?stream_id=teststream") as ws:
            batch = [
                {"type": "rendezvous", "data": "stream1"},
                {"type": "rendezvous", "data": "stream2"}
            ]
            packed = msgpack.packb(batch)
            compressed = zlib.compress(packed)
            await ws.send_bytes(compressed)
            # Receive responses for each item in batch
            for _ in range(2):
                msg = await ws.receive()
                assert msg.type == web.WSMsgType.BINARY
                resp = msgpack.unpackb(zlib.decompress(msg.data), raw=False)
                assert resp["stream_id"] == "teststream"
                assert resp["status"] == "ok"