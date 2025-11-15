""" 
Libra Tor Manager: Handles Tor integration, ephemeral onion service setup, and process isolation.
"""
import os
import subprocess
import tempfile
import time
from stem.control import Controller
from stem import Signal, SocketClosed

class TorManager:
    def __init__(self, tor_path='tor', control_port=9051, password=None, data_dir=None):
        import zlib
        self.tor_path = tor_path
        self.control_port = control_port
        self.password = password
        self.data_dir = data_dir or tempfile.mkdtemp(prefix='libra_tor_')
        self.controller = None
        self.tor_process = None
        self.circuit_cache = {}  # {peer_id: circuit_id}
        self.zlib = zlib

    def start_tor(self):
        # Start Tor in isolated environment (container/sandbox logic to be added)
        tor_cmd = [
            self.tor_path,
            '--ControlPort', str(self.control_port),
            '--DataDirectory', self.data_dir,
            '--CookieAuthentication', '1'  # Enable cookie authentication for security
        ]
        self.tor_process = subprocess.Popen(tor_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for Tor to be ready (poll control port with timeout)
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                self.controller = Controller.from_port(port=self.control_port)
                self.controller.authenticate(password=self.password)
                return  # Successfully connected
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Failed to connect to Tor after {max_attempts} attempts: {e}")
                time.sleep(0.5)

    def create_ephemeral_onion_service(self, port, peer_id=None):
        if not self.controller:
            raise RuntimeError("Tor is not started. Call start_tor() first.")
        # Check for cached circuit
        if peer_id and peer_id in self.circuit_cache:
            circuit_id = self.circuit_cache[peer_id]
            # Reuse circuit (simulate, actual reuse may require more logic)
            onion_address = circuit_id + '.onion'
            return onion_address, None
        # Create ephemeral v3 onion service
        result = self.controller.create_ephemeral_hidden_service({port: port}, await_publication=True)
        onion_address = result.service_id + '.onion'
        if peer_id:
            self.circuit_cache[peer_id] = result.service_id
        return onion_address, result.private_key
    def compress_data(self, data: bytes) -> bytes:
        """Compress data using zlib before transmission."""
        return self.zlib.compress(data)

    def decompress_data(self, data: bytes) -> bytes:
        """Decompress data using zlib after reception."""
        return self.zlib.decompress(data)

    def stop_tor(self):
        """Gracefully stop Tor process and clean up resources."""
        if self.controller:
            try:
                self.controller.signal(Signal.SHUTDOWN)
                self.controller.close()
            except SocketClosed:
                pass  # Already closed, ignore
            except Exception as e:
                print(f"Warning: Error closing controller: {e}")
            finally:
                self.controller = None
        
        if self.tor_process:
            try:
                # Wait for process to exit gracefully (5 second timeout)
                self.tor_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't exit gracefully
                self.tor_process.kill()
                self.tor_process.wait()
            finally:
                for stream in (self.tor_process.stdout, self.tor_process.stderr):
                    if stream:
                        stream.close()
                self.tor_process = None

    def __del__(self):
        """Destructor - ensure cleanup happens even if stop_tor() not called."""
        try:
            self.stop_tor()
        except Exception:
            pass  # Ignore errors during cleanup# Example usage:
# tor_mgr = TorManager()
# tor_mgr.start_tor()
# onion, key = tor_mgr.create_ephemeral_onion_service(12345)
# print('Onion address:', onion)
# tor_mgr.stop_tor()
