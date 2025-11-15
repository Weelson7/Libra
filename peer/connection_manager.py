import socket
import ssl
import threading
import json

class ConnectionManager:
        import msgpack
        from utils.crypto_utils import hybrid_encrypt, hybrid_decrypt, serialize_public_key, load_public_key

            def secure_rendezvous(self, tor_socket, peer_pubkey_pem, session_info, nat_info):
                """
                Exchange public keys, session info, and NAT traversal data over Tor using authenticated encryption and msgpack serialization.
                """
                # Prepare rendezvous payload
                payload = {
                    "type": "rendezvous",
                    "public_key": serialize_public_key(self.my_info['public_key']) if isinstance(self.my_info['public_key'], bytes) else self.my_info['public_key'],
                    "session_info": session_info,
                    "nat_info": nat_info
                }
                packed = msgpack.packb(payload)
                peer_pubkey = load_public_key(peer_pubkey_pem)
                encrypted = hybrid_encrypt(peer_pubkey, packed)
                tor_socket.sendall(encrypted.encode('utf-8'))

            def receive_rendezvous(self, tor_socket, my_privkey):
                """
                Receive and decrypt rendezvous payload over Tor.
                """
                data = tor_socket.recv(4096)
                decrypted = hybrid_decrypt(my_privkey, data.decode('utf-8'))
                payload = msgpack.unpackb(decrypted, raw=False)
                return payload
        def send_file_chunks(self, client_socket, file_path, chunk_size=64*1024, progress_callback=None):
            import os
            from utils.file_transfer import split_file
            file_size = os.path.getsize(file_path)
            sent = 0
            for seq, chunk in split_file(file_path):
                msg = {
                    "type": "file_chunk",
                    "seq": seq,
                    "data": chunk.hex(),
                    "file_name": os.path.basename(file_path),
                    "file_size": file_size
                }
                self.send_message(client_socket, msg)
                sent += len(chunk)
                if progress_callback:
                    progress_callback(sent, file_size)

        def receive_file_chunks(self, client_socket, output_path, expected_size, chunk_count, progress_callback=None):
            from utils.file_transfer import reassemble_file
            received_chunks = []
            total_received = 0
            while len(received_chunks) < chunk_count:
                data = client_socket.recv(1024*128)
                if not data:
                    break
                msg = json.loads(data.decode('utf-8'))
                if msg.get("type") == "file_chunk":
                    seq = msg["seq"]
                    chunk = bytes.fromhex(msg["data"])
                    received_chunks.append((seq, chunk))
                    total_received += len(chunk)
                    if progress_callback:
                        progress_callback(total_received, expected_size)
            reassemble_file(received_chunks, output_path)
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.connections = {}
        self.peers = {}  # id: {id, ip, nickname, public_key, fingerprint, blocked}
        self._load_peers()

    def _load_peers(self):
        """Load peers from disk (peers.json)."""
        try:
            with open('peers.json', 'r') as f:
                self.peers = json.load(f)
        except Exception:
            self.peers = {}

    def _save_peers(self):
        """Save peers to disk."""
        try:
            with open('peers.json', 'w') as f:
                json.dump(self.peers, f)
        except Exception as e:
            print(f"Error saving peers: {e}")
        self.my_info = {
            'id': 'my_id',
            'ip': '127.0.0.1',
            'nickname': 'Me',
            'public_key': 'my_public_key',
            'fingerprint': 'my_fingerprint'
        }
        self.lock = threading.Lock()
    def get_peers(self):
        """Return list of peer dicts for UI."""
        return list(self.peers.values())

    def connect_to_peer(self, ip_port, db_handler=None):
        """Connect to peer by IP:PORT string. Triggers pending message retry if db_handler is provided."""
        try:
            host, port = ip_port.split(":")
            port = int(port)
            sock = self._connect_to_peer(host, port)
            peer_id = f"peer_{host}_{port}"
            self.peers[peer_id] = {
                'id': peer_id,
                'ip': ip_port,
                'nickname': ip_port,
                'public_key': 'peer_public_key',
                'fingerprint': 'peer_fingerprint',
                'blocked': False
            }
            # Trigger retry of pending messages for this peer
            if db_handler:
                def send_func(msg):
                    try:
                        self.send_message(sock, {"message_id": msg["message_id"], "content": msg["content"].decode("utf-8")})
                        # Wait for ACK in production
                        return True
                    except Exception as e:
                        print(f"Send failed: {e}")
                        return False
                db_handler.retry_pending_messages(peer_id, send_func)
            return True
        except Exception as e:
            print(f"Error connecting to peer: {e}")
            return False

    def _connect_to_peer(self, host, port):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(cafile='server.crt')
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket = context.wrap_socket(client_socket, server_hostname=host)
        client_socket.connect((host, port))
        print(f"Connected to peer {host}:{port}")
        return client_socket

    def toggle_block_peer(self, peer_id):
        if peer_id in self.peers:
            self.peers[peer_id]['blocked'] = not self.peers[peer_id]['blocked']
            self._save_peers()

    def set_peer_nickname(self, peer_id, nickname):
        if peer_id in self.peers:
            self.peers[peer_id]['nickname'] = nickname
            self._save_peers()

    def remove_peer(self, peer_id):
        if peer_id in self.peers:
            del self.peers[peer_id]
            self._save_peers()

    def get_my_info(self):
        return self.my_info

    def create_server_socket(self, host, port):
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile='server.crt', keyfile='server.key')

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(self.max_connections)
        server_socket = context.wrap_socket(server_socket, server_side=True)

        print(f"Server listening on {host}:{port}")
        return server_socket

    def accept_connections(self, server_socket):
        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection accepted from {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket, addr)).start()

    def handle_client(self, client_socket, addr, db_handler=None):
        try:
            with self.lock:
                self.connections[addr] = client_socket

            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode('utf-8'))
                print(f"Received message from {addr}: {message}")

                # If ACK received, mark as delivered
                if db_handler and message.get("status") == "received" and "message_id" in message:
                    db_handler.mark_message_delivered(message["message_id"])

                # Echo the message back for now
                client_socket.send(json.dumps({"status": "received", "message_id": message.get("message_id")}).encode('utf-8'))
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            with self.lock:
                del self.connections[addr]
            client_socket.close()
            print(f"Connection closed for {addr}")

    def connect_to_peer(self, host, port):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(cafile='server.crt')

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket = context.wrap_socket(client_socket, server_hostname=host)
        client_socket.connect((host, port))
        print(f"Connected to peer {host}:{port}")
        return client_socket

    def send_message(self, client_socket, message):
        try:
            client_socket.send(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Error sending message: {e}")

    def close_all_connections(self):
        with self.lock:
            for addr, conn in self.connections.items():
                conn.close()
            self.connections.clear()
        print("All connections closed.")