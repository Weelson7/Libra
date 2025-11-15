"""
Libra Tor Manager: Handles Tor integration, ephemeral onion service setup, and process isolation.
"""
import os
import subprocess
import tempfile
from stem.control import Controller
from stem import Signal

class TorManager:
    def __init__(self, tor_path='tor', control_port=9051, password=None, data_dir=None):
        self.tor_path = tor_path
        self.control_port = control_port
        self.password = password
        self.data_dir = data_dir or tempfile.mkdtemp(prefix='libra_tor_')
        self.controller = None
        self.tor_process = None

    def start_tor(self):
        # Start Tor in isolated environment (container/sandbox logic to be added)
        tor_cmd = [self.tor_path, '--ControlPort', str(self.control_port), '--DataDirectory', self.data_dir]
        print(f"[TorManager] Starting Tor with command: {tor_cmd}")
        try:
            self.tor_process = subprocess.Popen(tor_cmd)
        except FileNotFoundError as e:
            print(f"[TorManager] ERROR: Tor executable not found: {self.tor_path}")
            raise
        except Exception as e:
            print(f"[TorManager] ERROR: Failed to start Tor: {e}")
            raise
        # Wait for Tor to be ready
        try:
            self.controller = Controller.from_port(port=self.control_port)
            self.controller.authenticate(password=self.password)
        except Exception as e:
            print(f"[TorManager] ERROR: Failed to connect/authenticate to Tor control port: {e}")
            raise

    def create_ephemeral_onion_service(self, port):
        # Create ephemeral v3 onion service
        result = self.controller.create_ephemeral_hidden_service({port: port}, await_publication=True)
        onion_address = result.service_id + '.onion'
        return onion_address, result.private_key

    def stop_tor(self):
        if self.controller:
            self.controller.signal(Signal.SHUTDOWN)
            self.controller.close()
        if self.tor_process:
            self.tor_process.terminate()

    def __del__(self):
        self.stop_tor()

    def wait_for_tor_bootstrap(self, timeout=60):
        """Wait until Tor is fully bootstrapped (100%) or timeout (seconds)"""
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                status = self.controller.get_info("status/bootstrap-phase")
                if status and "100%" in status:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

# Example usage:
# tor_mgr = TorManager()
# tor_mgr.start_tor()
# onion, key = tor_mgr.create_ephemeral_onion_service(12345)
# print('Onion address:', onion)
# tor_mgr.stop_tor()
