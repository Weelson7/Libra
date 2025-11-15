import unittest
from unittest.mock import MagicMock
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from peer.connection_manager import ConnectionManager

class TestDirectP2PPhase4(unittest.TestCase):
    def setUp(self):
        self.cm = ConnectionManager()
        self.cm.my_info = {
            'id': 'my_id',
            'ip': '127.0.0.1',
            'nickname': 'Me',
            'public_key': 'my_public_key',
            'fingerprint': 'my_fingerprint'
        }

    def test_attempt_direct_p2p_timeout(self):
        # Simulate missing NAT info, should fallback to Tor
        peer_nat_info = {}
        peer_pubkey_pem = 'dummy_pubkey'
        session_info = {'session': 'test'}
        tor_socket = MagicMock()
        result = self.cm.attempt_direct_p2p(peer_nat_info, peer_pubkey_pem, session_info, tor_socket, timeout=1)
        self.assertEqual(result['channel'], 'tor')
        self.assertEqual(result['socket'], tor_socket)

    def test_attempt_direct_p2p_fail(self):
        # Simulate invalid NAT info, should fallback to Tor
        peer_nat_info = {'external_ip': '256.256.256.256', 'external_port': 9999}
        peer_pubkey_pem = 'dummy_pubkey'
        session_info = {'session': 'test'}
        tor_socket = MagicMock()
        result = self.cm.attempt_direct_p2p(peer_nat_info, peer_pubkey_pem, session_info, tor_socket, timeout=1)
        self.assertEqual(result['channel'], 'tor')
        self.assertEqual(result['socket'], tor_socket)

    def test_monitor_connection_health_fallback(self):
        # Simulate socket failure, should fallback to Tor
        failing_sock = MagicMock()
        failing_sock.send.side_effect = Exception('fail')
        fallback_sock = MagicMock()
        result = self.cm.monitor_connection_health(failing_sock, fallback_sock, check_interval=0.1)
        self.assertEqual(result, fallback_sock)

    def test_send_message_auto_direct(self):
        # Simulate direct connection success and fallback
        def fake_attempt(*args, **kwargs):
            return {'channel': 'direct', 'socket': MagicMock()}
        def fake_monitor(sock, fallback, check_interval=5):
            return fallback
        self.cm.attempt_direct_p2p = fake_attempt
        self.cm.monitor_connection_health = fake_monitor
        self.cm.send_message = MagicMock()
        peer_nat_info = {'external_ip': '1.2.3.4', 'external_port': 1234}
        peer_pubkey_pem = 'dummy_pubkey'
        session_info = {'session': 'test'}
        tor_socket = MagicMock()
        message = {'msg': 'hello'}
        channel = self.cm.send_message_auto(peer_nat_info, peer_pubkey_pem, session_info, tor_socket, message)
        self.assertEqual(channel, 'direct')

if __name__ == '__main__':
    unittest.main()
