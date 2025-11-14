import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiohttp import web

class TunnelHandler:
    def __init__(self, stun_server="stun:stun.l.google.com:19302", turn_server=None, turn_username=None, turn_password=None):
        self.stun_server = stun_server
        self.turn_server = turn_server
        self.turn_username = turn_username
        self.turn_password = turn_password
        self.peer_connection = None

    async def create_webrtc_connection(self):
        self.peer_connection = RTCPeerConnection({
            "iceServers": [
                {"urls": [self.stun_server]},
                {"urls": [self.turn_server], "username": self.turn_username, "credential": self.turn_password} if self.turn_server else {}
            ]
        })
        return self.peer_connection

    async def handle_offer(self, offer):
        self.peer_connection = await self.create_webrtc_connection()
        await self.peer_connection.setRemoteDescription(RTCSessionDescription(sdp=offer["sdp"], type=offer["type"]))
        answer = await self.peer_connection.createAnswer()
        await self.peer_connection.setLocalDescription(answer)
        return {
            "sdp": self.peer_connection.localDescription.sdp,
            "type": self.peer_connection.localDescription.type
        }

    async def https_tunnel(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                await ws.send_str(f"Echo: {msg.data}")
            elif msg.type == web.WSMsgType.ERROR:
                print(f"WebSocket connection closed with exception {ws.exception()}")

        return ws

# Example usage
if __name__ == "__main__":
    handler = TunnelHandler()

    app = web.Application()
    app.router.add_post("/webrtc", handler.https_tunnel)

    web.run_app(app, port=8080)