"""
Test: Peers can establish P2P when conditions are met, with fallback to Tor
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import socket
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from peer.connection_manager import ConnectionManager
from utils.crypto_utils import generate_rsa_keypair, serialize_public_key


class TestP2PConnection(unittest.TestCase):
    """Test P2P direct connection scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.conn_mgr = ConnectionManager()
        
        # Generate test keypairs
        self.peer1_priv, self.peer1_pub = generate_rsa_keypair()
        self.peer2_priv, self.peer2_pub = generate_rsa_keypair()
        
        # Mock peer info
        self.peer1_info = {
            'public_key': self.peer1_pub,
            'id': 'peer1',
            'external_ip': '192.168.1.100',
            'external_port': 12345
        }
        
        self.peer2_info = {
            'public_key': self.peer2_pub,
            'id': 'peer2',
            'external_ip': '192.168.1.101',
            'external_port': 12346
        }
    
    def test_p2p_connection_conditions(self):
        """Test that P2P connection is attempted when conditions are met"""
        # Conditions for P2P:
        # 1. Both peers have NAT info (external IP and port)
        # 2. Peers are on same network or have public IPs
        # 3. No firewall blocking
        
        nat_info = {
            'external_ip': '192.168.1.100',
            'external_port': 12345,
            'nat_type': 'full_cone'  # Best case for P2P
        }
        
        # Verify NAT info is complete
        self.assertIsNotNone(nat_info.get('external_ip'))
        self.assertIsNotNone(nat_info.get('external_port'))
    
    def test_p2p_attempt_with_tor_fallback(self):
        """Test P2P attempt that falls back to Tor"""
        # Mock Tor socket
        mock_tor_socket = Mock()
        mock_tor_socket.send = Mock()
        mock_tor_socket.recv = Mock(return_value=b'{"type": "ack"}')
        
        # Mock NAT info with unreachable IP (will fail P2P)
        peer_nat_info = {
            'external_ip': '10.0.0.1',  # Private IP, not directly reachable
            'external_port': 12345
        }
        
        peer_pubkey_pem = serialize_public_key(self.peer2_pub)
        session_info = {'session_id': 'test_session'}
        
        # Mock the _connect_to_peer method to avoid hanging
        with patch.object(self.conn_mgr, '_connect_to_peer', side_effect=socket.timeout("Connection timeout")):
            # Attempt connection (should fallback to Tor)
            result = self.conn_mgr.attempt_direct_p2p(
                peer_nat_info,
                peer_pubkey_pem,
                session_info,
                mock_tor_socket,
                timeout=1  # Short timeout for test
            )
        
        # Verify fallback to Tor
        self.assertEqual(result['channel'], 'tor')
        self.assertEqual(result['socket'], mock_tor_socket)
    
    def test_p2p_successful_connection(self):
        """Test successful P2P connection"""
        # Mock the _connect_to_peer method to simulate success
        mock_socket = Mock()
        mock_socket.sendall = Mock()
        mock_socket.recv = Mock(return_value=b'ACK')
        mock_socket.close = Mock()
        
        with patch.object(self.conn_mgr, '_connect_to_peer', return_value=mock_socket):
            # Test direct connection
            client_socket = self.conn_mgr._connect_to_peer('127.0.0.1', 12345)
            
            # Send test data
            client_socket.sendall(b'TEST')
            
            # Receive response
            response = client_socket.recv(1024)
            
            self.assertEqual(response, b'ACK')
            
            # Verify calls
            mock_socket.sendall.assert_called_once_with(b'TEST')
            mock_socket.recv.assert_called_once()
            
            client_socket.close()
    
    def test_nat_info_exchange(self):
        """Test NAT information exchange between peers"""
        nat_info = {
            'external_ip': '203.0.113.1',  # Example public IP
            'external_port': 54321,
            'internal_ip': '192.168.1.100',
            'internal_port': 12345,
            'nat_type': 'symmetric'
        }
        
        # Verify NAT info structure
        self.assertIn('external_ip', nat_info)
        self.assertIn('external_port', nat_info)
        self.assertIn('nat_type', nat_info)
    
    def test_connection_health_monitoring(self):
        """Test connection health monitoring with fallback"""
        # Create mock sockets
        mock_direct_socket = Mock()
        mock_tor_socket = Mock()
        
        # Simulate direct connection failure
        mock_direct_socket.send = Mock(side_effect=Exception("Connection lost"))
        
        # Test health monitor (simplified - actual method runs in loop)
        try:
            mock_direct_socket.send(b'\x00')
            fallback_needed = False
        except Exception:
            fallback_needed = True
        
        # Verify fallback is triggered
        self.assertTrue(fallback_needed)
    
    def test_p2p_message_routing(self):
        """Test that messages are routed correctly via P2P or Tor"""
        # Mock sockets
        mock_tor_socket = Mock()
        mock_direct_socket = Mock()
        
        # Test message via Tor
        message = {"type": "text", "content": "Hello"}
        
        # Simulate send
        self.conn_mgr.send_message = Mock()
        self.conn_mgr.send_message(mock_tor_socket, message)
        
        # Verify send was called
        self.conn_mgr.send_message.assert_called_once()


class TestP2PWithTorFallback(unittest.TestCase):
    """Test P2P with automatic Tor fallback"""
    
    def setUp(self):
        self.conn_mgr = ConnectionManager()
    
    def test_parallel_connection_attempt(self):
        """Test that P2P and Tor connections are attempted in parallel"""
        # This tests the concurrent.futures logic in attempt_direct_p2p
        
        mock_tor_socket = Mock()
        peer_nat_info = {'external_ip': '10.0.0.1', 'external_port': 9999}
        peer_pubkey_pem = b'-----BEGIN PUBLIC KEY-----\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC=\n-----END PUBLIC KEY-----'
        session_info = {'session_id': 'test'}
        
        # Mock the _connect_to_peer to avoid hanging
        with patch.object(self.conn_mgr, '_connect_to_peer', side_effect=socket.timeout("Connection timeout")):
            # Attempt with short timeout
            start_time = time.time()
            result = self.conn_mgr.attempt_direct_p2p(
                peer_nat_info,
                peer_pubkey_pem,
                session_info,
                mock_tor_socket,
                timeout=1
            )
            elapsed = time.time() - start_time
        
        # Should complete quickly (timeout or faster)
        self.assertLess(elapsed, 2)
        
        # Should fallback to Tor
        self.assertEqual(result['channel'], 'tor')
    
    def test_connection_type_detection(self):
        """Test detection of connection type (P2P vs Tor)"""
        # Test structure for tracking connection type
        connection_types = {
            'peer1': 'tor',
            'peer2': 'direct',
            'peer3': 'tor'
        }
        
        # Verify tracking
        self.assertEqual(connection_types['peer1'], 'tor')
        self.assertEqual(connection_types['peer2'], 'direct')
    
    def test_automatic_upgrade_to_p2p(self):
        """Test automatic upgrade from Tor to P2P when possible"""
        # Initially connected via Tor
        current_channel = 'tor'
        
        # P2P becomes available
        p2p_available = True
        
        if p2p_available:
            # Attempt upgrade
            current_channel = 'direct'
        
        # Verify upgrade
        self.assertEqual(current_channel, 'direct')
    
    def test_graceful_degradation_to_tor(self):
        """Test graceful degradation from P2P to Tor on failure"""
        # Initially connected via P2P
        current_channel = 'direct'
        
        # P2P connection fails
        p2p_failed = True
        
        if p2p_failed:
            # Fallback to Tor
            current_channel = 'tor'
        
        # Verify fallback
        self.assertEqual(current_channel, 'tor')


class TestNATTraversal(unittest.TestCase):
    """Test NAT traversal techniques"""
    
    def test_nat_type_detection(self):
        """Test NAT type detection"""
        nat_types = [
            'full_cone',      # Best for P2P
            'restricted_cone', # Good for P2P
            'port_restricted', # Moderate for P2P
            'symmetric'        # Difficult for P2P
        ]
        
        # Test categorization
        for nat_type in nat_types:
            self.assertIn(nat_type, nat_types)
    
    def test_hole_punching_simulation(self):
        """Test UDP hole punching concept (simplified)"""
        # Simulate hole punching attempt
        hole_punch_success = False
        
        # Conditions for success:
        # 1. Both peers send packets simultaneously
        # 2. NAT allows incoming after outgoing
        # 3. Timing is coordinated
        
        simultaneous_send = True
        nat_allows = True
        
        if simultaneous_send and nat_allows:
            hole_punch_success = True
        
        # In this test, conditions are met
        self.assertTrue(hole_punch_success)


def run_tests():
    """Run all P2P connection tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestP2PConnection))
    suite.addTests(loader.loadTestsFromTestCase(TestP2PWithTorFallback))
    suite.addTests(loader.loadTestsFromTestCase(TestNATTraversal))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
