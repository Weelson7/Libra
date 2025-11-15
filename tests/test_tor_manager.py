"""
Test script for Libra TorManager
"""
import unittest
import sys
import os
# Add project root to sys.path for reliable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.tor_manager import TorManager
import config

class TestTorManager(unittest.TestCase):
    def test_tor_startup_and_onion_service(self):
        tor_mgr = TorManager(
            tor_path=config.TOR_PATH,
            control_port=config.TOR_CONTROL_PORT,
            password=config.TOR_PASSWORD
        )
        try:
            tor_mgr.start_tor()
            onion, key = tor_mgr.create_ephemeral_onion_service(12345)
            print('Onion address:', onion)
            self.assertTrue(onion.endswith('.onion'))
            self.assertIsNotNone(key)
        finally:
            tor_mgr.stop_tor()

if __name__ == '__main__':
    unittest.main()
