import socket
import ssl
import threading
import json

class ConnectionManager:
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.connections = {}
        self.lock = threading.Lock()

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

    def handle_client(self, client_socket, addr):
        try:
            with self.lock:
                self.connections[addr] = client_socket

            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode('utf-8'))
                print(f"Received message from {addr}: {message}")

                # Echo the message back for now
                client_socket.send(json.dumps({"status": "received"}).encode('utf-8'))
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