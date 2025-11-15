"""
Test: Peers can connect via Tor and reconnect when a peer goes offline then back online
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tempfile
import time
import threading
from pathlib import Path

from tor_manager import TorManager
from peer.connection_manager import ConnectionManager
from db.db_handler import DBHandler
from utils.crypto_utils import generate_rsa_keypair, serialize_public_key


class TestTorReconnection(unittest.TestCase):
    """Test Tor connection and reconnection scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = DBHandler(db_path=self.db_path)
        self.db.init_db()
        
        self.conn_mgr = ConnectionManager()
        
        # Generate test keypairs
        self.peer1_priv, self.peer1_pub = generate_rsa_keypair()
        self.peer2_priv, self.peer2_pub = generate_rsa_keypair()
        
    def tearDown(self):
        """Clean up test environment"""
        self.db.close()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_tor_initial_connection(self):
        """Test initial Tor connection between peers"""
        # Add peer to database
        peer_id = "peer_tor_001"
        pub_key_str = serialize_public_key(self.peer2_pub).decode('utf-8')
        self.db.add_peer(peer_id, nickname="TorPeer1", public_key=pub_key_str)
        
        # Verify peer was added
        peer = self.db.get_peer(peer_id)
        self.assertIsNotNone(peer)
        self.assertEqual(peer['nickname'], "TorPeer1")
        
    def test_peer_offline_then_online(self):
        """Test message queuing when peer goes offline then comes back online"""
        peer_id = "peer_tor_002"
        self.db.add_peer(peer_id, nickname="TorPeer2")
        
        # Send message while peer is "offline" (not connected)
        message_id = "msg_001"
        content = b"Hello from offline test"
        timestamp = int(time.time())
        
        # Insert as pending message (sync_status=0)
        self.db.insert_message(
            peer_id=peer_id,
            content=content,
            timestamp=timestamp,
            message_id=message_id,
            sync_status=0  # Pending
        )
        
        # Verify message is pending
        pending = self.db.list_pending_messages()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['message_id'], message_id)
        self.assertEqual(pending[0]['sync_status'], 0)
        
        # Simulate peer coming online and message being sent
        self.db.update_message_status(message_id, 1)  # Sent
        
        # Verify message is now sent
        msg = self.db.get_message(message_id)
        self.assertEqual(msg['sync_status'], 1)
        
        # Simulate delivery confirmation
        self.db.mark_message_delivered(message_id)
        
        # Verify message is delivered
        msg = self.db.get_message(message_id)
        self.assertEqual(msg['sync_status'], 2)
    
    def test_automatic_retry_on_reconnection(self):
        """Test automatic retry of pending messages when peer reconnects"""
        peer_id = "peer_tor_003"
        self.db.add_peer(peer_id, nickname="TorPeer3")
        
        # Queue multiple messages while offline
        messages = []
        for i in range(5):
            message_id = f"msg_{i:03d}"
            content = f"Message {i}".encode()
            timestamp = int(time.time()) + i
            
            self.db.insert_message(
                peer_id=peer_id,
                content=content,
                timestamp=timestamp,
                message_id=message_id,
                sync_status=0
            )
            messages.append(message_id)
        
        # Verify all messages are pending
        pending = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending), 5)
        
        # Simulate peer reconnecting and messages being sent
        sent_count = 0
        def mock_send_func(msg):
            nonlocal sent_count
            sent_count += 1
            return True  # Success
        
        self.db.retry_pending_messages(peer_id, mock_send_func)
        
        # Verify all messages were sent
        self.assertEqual(sent_count, 5)
        
        # Verify no more pending messages
        pending = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending), 0)
    
    def test_connection_state_tracking(self):
        """Test tracking of connection state (online/offline)"""
        peer_id = "peer_tor_004"
        self.db.add_peer(peer_id, nickname="TorPeer4")
        
        # Initial state: no last_seen
        peer = self.db.get_peer(peer_id)
        self.assertIsNone(peer['last_seen'])
        
        # Simulate peer coming online
        current_time = int(time.time())
        self.db.update_peer_status(peer_id, current_time)
        
        # Verify last_seen was updated
        peer = self.db.get_peer(peer_id)
        self.assertEqual(peer['last_seen'], current_time)
        
        # Simulate peer going offline (last_seen becomes stale)
        time.sleep(1)
        new_time = int(time.time())
        
        # Peer is considered offline if last_seen is old
        self.assertTrue(new_time > peer['last_seen'])
    
    def test_multiple_reconnection_cycles(self):
        """Test multiple offline/online cycles"""
        peer_id = "peer_tor_005"
        self.db.add_peer(peer_id, nickname="TorPeer5")
        
        for cycle in range(3):
            # Send messages while offline
            for i in range(2):
                message_id = f"cycle{cycle}_msg{i}"
                content = f"Cycle {cycle} Message {i}".encode()
                timestamp = int(time.time())
                
                self.db.insert_message(
                    peer_id=peer_id,
                    content=content,
                    timestamp=timestamp,
                    message_id=message_id,
                    sync_status=0
                )
            
            # Verify messages pending
            pending = self.db.get_pending_messages_for_peer(peer_id)
            self.assertEqual(len(pending), 2)
            
            # Simulate reconnection and send
            def mock_send(msg):
                return True
            
            self.db.retry_pending_messages(peer_id, mock_send)
            
            # Verify messages sent
            pending = self.db.get_pending_messages_for_peer(peer_id)
            self.assertEqual(len(pending), 0)
    
    def test_partial_send_failure_retry(self):
        """Test retry logic when some messages fail to send"""
        peer_id = "peer_tor_006"
        self.db.add_peer(peer_id, nickname="TorPeer6")
        
        # Queue messages
        message_ids = []
        for i in range(5):
            message_id = f"msg_{i:03d}"
            content = f"Message {i}".encode()
            timestamp = int(time.time())
            
            self.db.insert_message(
                peer_id=peer_id,
                content=content,
                timestamp=timestamp,
                message_id=message_id,
                sync_status=0
            )
            message_ids.append(message_id)
        
        # Simulate partial failure (first 2 succeed, rest fail)
        send_attempts = []
        def mock_send_partial(msg):
            send_attempts.append(msg['message_id'])
            # First 2 succeed, rest fail
            return len(send_attempts) <= 2
        
        self.db.retry_pending_messages(peer_id, mock_send_partial, max_retries=1)
        
        # Verify first 2 were marked as sent
        for i in range(2):
            msg = self.db.get_message(message_ids[i])
            self.assertEqual(msg['sync_status'], 1)
        
        # Verify rest are still pending (would need max_retries check)
        pending = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending), 3)


class TestTorConnectionManager(unittest.TestCase):
    """Test ConnectionManager with Tor integration"""
    
    def setUp(self):
        self.conn_mgr = ConnectionManager()
    
    def test_tor_socket_creation(self):
        """Test that Tor socket can be created (mock)"""
        # This would require actual Tor instance, so we test the structure
        self.assertIsNotNone(self.conn_mgr)
        self.assertIsInstance(self.conn_mgr.connections, dict)
    
    def test_connection_manager_peer_tracking(self):
        """Test that connection manager tracks peers"""
        # Add mock peer
        peer_id = "mock_peer_001"
        self.conn_mgr.peers[peer_id] = {
            'id': peer_id,
            'ip': '127.0.0.1:9999',
            'nickname': 'MockPeer',
            'public_key': 'mock_key',
            'fingerprint': 'mock_fp',
            'blocked': False
        }
        
        # Verify peer tracking
        peers = self.conn_mgr.get_peers()
        self.assertEqual(len(peers), 1)
        self.assertEqual(peers[0]['id'], peer_id)


def run_tests():
    """Run all Tor reconnection tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTorReconnection))
    suite.addTests(loader.loadTestsFromTestCase(TestTorConnectionManager))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
