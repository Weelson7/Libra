import unittest
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from peer.connection_manager import ConnectionManager

class TestDirectP2PSuccess(unittest.TestCase):
    def setUp(self):
        self.cm = ConnectionManager()
        self.cm.my_info = {
            'id': 'my_id',
            'ip': '127.0.0.1',
            'nickname': 'Me',
            'public_key': 'my_public_key',
            'fingerprint': 'my_fingerprint'
        }

    @patch('peer.connection_manager.hybrid_encrypt')
    @patch('peer.connection_manager.serialize_public_key')
    @patch('peer.connection_manager.load_public_key')
    @patch('peer.connection_manager.ConnectionManager._connect_to_peer')
    def test_direct_p2p_connection_success(self, mock_connect, mock_load_key, mock_serialize, mock_encrypt):
        """Test successful direct P2P connection establishment"""
        # Mock successful socket connection
        mock_sock = MagicMock()
        mock_connect.return_value = mock_sock
        
        # Mock crypto functions
        mock_load_key.return_value = MagicMock()
        mock_serialize.return_value = 'serialized_key'
        mock_encrypt.return_value = 'encrypted_data'
        
        peer_nat_info = {'external_ip': '127.0.0.1', 'external_port': 8888}
        peer_pubkey_pem = 'dummy_pubkey'
        session_info = {'session': 'test'}
        tor_socket = MagicMock()
        
        result = self.cm.attempt_direct_p2p(peer_nat_info, peer_pubkey_pem, session_info, tor_socket, timeout=2)
        
        # Verify direct connection was attempted and succeeded
        self.assertEqual(result['channel'], 'direct')
        self.assertIsNotNone(result['socket'])
        mock_connect.assert_called_once_with('127.0.0.1', 8888)
        print("test_direct_p2p_connection_success: PASS")

    def test_empty_nat_info_fallback(self):
        """Test that empty NAT info correctly falls back to Tor"""
        peer_nat_info = {}
        peer_pubkey_pem = 'dummy_pubkey'
        session_info = {'session': 'test'}
        tor_socket = MagicMock()
        
        result = self.cm.attempt_direct_p2p(peer_nat_info, peer_pubkey_pem, session_info, tor_socket, timeout=1)
        
        self.assertEqual(result['channel'], 'tor')
        self.assertEqual(result['socket'], tor_socket)
        print("test_empty_nat_info_fallback: PASS")

    def test_connection_health_monitor_healthy(self):
        """Test that healthy connections continue without fallback"""
        # Mock a healthy socket that doesn't raise exceptions
        healthy_sock = MagicMock()
        healthy_sock.send.return_value = 1
        fallback_sock = MagicMock()
        
        # Create a counter to stop the infinite loop after a few iterations
        call_count = [0]
        def side_effect(*args):
            call_count[0] += 1
            if call_count[0] > 3:
                raise KeyboardInterrupt()  # Stop the loop
            return 1
        
        healthy_sock.send.side_effect = side_effect
        
        try:
            result = self.cm.monitor_connection_health(healthy_sock, fallback_sock, check_interval=0.01)
        except KeyboardInterrupt:
            # Expected - we stopped the loop ourselves
            pass
        
        # Verify we called send multiple times (healthy connection)
        self.assertGreater(healthy_sock.send.call_count, 1)
        print("test_connection_health_monitor_healthy: PASS")

    @patch('peer.connection_manager.ConnectionManager._connect_to_peer')
    def test_connect_to_peer_localhost(self, mock_connect):
        """Test connecting to localhost peer with proper mocking"""
        mock_sock = MagicMock()
        mock_connect.return_value = mock_sock
        
        # Use the IP:PORT format that the first connect_to_peer expects
        result = self.cm.connect_to_peer('127.0.0.1:8888')
        
        self.assertTrue(result)
        # Verify _connect_to_peer was called with split host and port
        mock_connect.assert_called_once_with('127.0.0.1', 8888)
        # Verify peer was added
        self.assertIn('peer_127.0.0.1_8888', self.cm.peers)
        print("test_connect_to_peer_localhost: PASS")

    def test_send_message_function(self):
        """Test that send_message properly formats and sends data"""
        mock_socket = MagicMock()
        message = {'type': 'test', 'data': 'hello'}
        
        self.cm.send_message(mock_socket, message)
        
        # Verify socket.send was called
        mock_socket.send.assert_called_once()
        # Verify the message was JSON-encoded
        call_args = mock_socket.send.call_args[0][0]
        self.assertIn(b'test', call_args)
        self.assertIn(b'hello', call_args)
        print("test_send_message_function: PASS")

if __name__ == '__main__':
    unittest.main()
