import asyncio
import json
import msgpack
from aiohttp import web

class TunnelHandler:
    # Simple in-memory rate limiter (per connection)
    _rate_limit_window = 5  # seconds
    _rate_limit_max = 10    # max messages per window
    _connection_times = {}

    def _is_rate_limited(self, connection_id):
        import time
        now = time.time()
        times = self._connection_times.get(connection_id, [])
        # Remove old timestamps
        times = [t for t in times if now - t < self._rate_limit_window]
        self._connection_times[connection_id] = times
        if len(times) >= self._rate_limit_max:
            return True
        self._connection_times[connection_id].append(now)
        return False

    def _authenticate_message(self, msg):
        # Placeholder for authentication logic (e.g., check signature, token)
        # Return True if authenticated, False otherwise
        return True if msg.get('type') else False
    """
    Handles NAT traversal for peer-to-peer connections using HTTPS tunneling.
    This is a simplified implementation that provides WebSocket-based tunneling.
    Full WebRTC support with aiortc can be added later when the package is properly installed.
    """
    
    def __init__(self, stun_server="stun:stun.l.google.com:19302", turn_server=None, turn_username=None, turn_password=None):
        import zlib
        self.stun_server = stun_server
        self.turn_server = turn_server
        self.turn_username = turn_username
        self.turn_password = turn_password
        self.connections = {}
        self.zlib = zlib

    async def handle_offer(self, offer):
        """
        Placeholder for WebRTC offer handling.
        Returns a mock answer for testing purposes.
        """
        return {
            "sdp": "v=0\no=- 46117317 2 IN IP4 127.0.0.1\ns=-\nt=0 0\na=sendrecv",
            "type": "answer"
        }

    async def https_tunnel(self, request):
        """
        Establishes an HTTPS tunnel using WebSocket for NAT traversal.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Store connection
        connection_id = id(ws)
        self.connections[connection_id] = ws
        stream_id = request.query.get('stream_id', 'default')

        try:
            async for msg in ws:
                # Message batching: accept msgpack-packed list of messages
                if msg.type == web.WSMsgType.BINARY:
                    try:
                        # Decompress if possible
                        try:
                            data = self.zlib.decompress(msg.data)
                        except Exception:
                            data = msg.data
                        batch = msgpack.unpackb(data, raw=False)
                        if isinstance(batch, list):
                            for item in batch:
                                # Add stream multiplexing tag
                                item['stream_id'] = stream_id
                                if self._is_rate_limited(connection_id):
                                    await ws.send_bytes(msgpack.packb({"status": "rate_limited"}))
                                    continue
                                if self._authenticate_message(item):
                                    resp = {"status": "ok", "type": item.get("type"), "stream_id": stream_id}
                                    await ws.send_bytes(self.zlib.compress(msgpack.packb(resp)))
                                else:
                                    resp = {"status": "auth_failed", "stream_id": stream_id}
                                    await ws.send_bytes(self.zlib.compress(msgpack.packb(resp)))
                        else:
                            resp = {"status": "invalid_batch", "stream_id": stream_id}
                            await ws.send_bytes(self.zlib.compress(msgpack.packb(resp)))
                    except Exception as e:
                        resp = {"status": "error", "error": str(e), "stream_id": stream_id}
                        await ws.send_bytes(self.zlib.compress(msgpack.packb(resp)))
                elif msg.type == web.WSMsgType.TEXT:
                    try:
                        item = json.loads(msg.data)
                        item['stream_id'] = stream_id
                        if self._is_rate_limited(connection_id):
                            await ws.send_str(json.dumps({"status": "rate_limited", "stream_id": stream_id}))
                            continue
                        if self._authenticate_message(item):
                            await ws.send_str(json.dumps({"status": "ok", "type": item.get("type"), "stream_id": stream_id}))
                        else:
                            await ws.send_str(json.dumps({"status": "auth_failed", "stream_id": stream_id}))
                    except Exception as e:
                        await ws.send_str(json.dumps({"status": "error", "error": str(e), "stream_id": stream_id}))
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"WebSocket connection closed with exception {ws.exception()}")
                    break
        finally:
            # Clean up connection
            if connection_id in self.connections:
                del self.connections[connection_id]

        return ws

    async def send_to_peer(self, connection_id, data):
        """
        Send data to a specific peer connection.
        """
        if connection_id in self.connections:
            ws = self.connections[connection_id]
            if isinstance(data, str):
                await ws.send_str(data)
            else:
                await ws.send_bytes(data)
            return True
        return False

# Example usage
if __name__ == "__main__":
    handler = TunnelHandler()

    app = web.Application()
    app.router.add_get("/webrtc", handler.https_tunnel)

    web.run_app(app, port=8080)