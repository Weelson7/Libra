import asyncio
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer, loop_context
from peer.tunnel_handler import TunnelHandler

@pytest.fixture
def stun_server():
    return "stun:stun.l.google.com:19302"

@pytest.fixture
def tunnel_handler(stun_server):
    return TunnelHandler(stun_server=stun_server)

@pytest.fixture
def aiohttp_client():
    with loop_context() as loop:
        app = web.Application()
        handler = TunnelHandler()
        app.router.add_post("/webrtc", handler.https_tunnel)
        server = TestServer(app)
        client = TestClient(server)
        loop.run_until_complete(client.start_server())
        yield client
        loop.run_until_complete(client.close())

@pytest.mark.asyncio
async def test_webrtc_offer(tunnel_handler):
    offer = {
        "sdp": "v=0\no=- 46117317 2 IN IP4 127.0.0.1\ns=-\nt=0 0\na=sendrecv",
        "type": "offer"
    }
    response = await tunnel_handler.handle_offer(offer)
    assert "sdp" in response
    assert "type" in response
    assert response["type"] == "answer"

@pytest.mark.asyncio
async def test_https_tunnel(aiohttp_client):
    async with aiohttp_client.ws_connect("/webrtc") as ws:
        await ws.send_str("Hello")
        msg = await ws.receive()
        assert msg.type == web.WSMsgType.TEXT
        assert msg.data == "Echo: Hello"