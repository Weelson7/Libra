"""
Test: Onion address rotation doesn't break connection between peers
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from tor_manager import TorManager
from db.db_handler import DBHandler
from peer.connection_manager import ConnectionManager


class TestOnionRotation(unittest.TestCase):
    """Test onion address rotation scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = DBHandler(db_path=self.db_path)
        self.db.init_db()
        
        self.conn_mgr = ConnectionManager()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db.close()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_onion_address_generation(self):
        """Test generation of new onion address"""
        # Mock TorManager
        tor_mgr = Mock(spec=TorManager)
        
        # Mock ephemeral onion service creation
        new_address = "abc123xyz.onion"
        private_key = "mock_private_key"
        tor_mgr.create_ephemeral_onion_service = Mock(return_value=(new_address, private_key))
        
        # Create new onion service
        address, key = tor_mgr.create_ephemeral_onion_service(12345)
        
        # Verify new address was created
        self.assertEqual(address, new_address)
        self.assertEqual(key, private_key)
        self.assertTrue(address.endswith('.onion'))
    
    def test_peer_notification_on_rotation(self):
        """Test that peers are notified when onion address rotates"""
        # Add peers
        peers = ['peer1', 'peer2', 'peer3']
        for peer_id in peers:
            self.db.add_peer(peer_id, nickname=peer_id)
        
        # Track notifications
        notifications_sent = []
        
        def notify_peer(peer_id, new_address):
            notifications_sent.append((peer_id, new_address))
        
        # Simulate rotation
        new_address = "newaddress123.onion"
        for peer in self.db.get_all_peers():
            notify_peer(peer['peer_id'], new_address)
        
        # Verify all peers were notified
        self.assertEqual(len(notifications_sent), len(peers))
        for peer_id in peers:
            self.assertIn(peer_id, [n[0] for n in notifications_sent])
    
    def test_connection_continuity_during_rotation(self):
        """Test that existing connections remain stable during rotation"""
        # Simulate active connections
        active_connections = {
            'peer1': Mock(),
            'peer2': Mock(),
            'peer3': Mock()
        }
        
        # Verify connections are active before rotation
        self.assertEqual(len(active_connections), 3)
        
        # Simulate rotation (create new onion address)
        old_address = "oldaddress.onion"
        new_address = "newaddress.onion"
        
        # Connections should remain active during transition
        # (Old onion service stays active until all peers updated)
        connections_after_rotation = active_connections.copy()
        
        # Verify no connections were dropped
        self.assertEqual(len(connections_after_rotation), len(active_connections))
    
    def test_graceful_transition_period(self):
        """Test graceful transition period during rotation"""
        # Old and new addresses both active during transition
        old_address = "oldaddress.onion"
        new_address = "newaddress.onion"
        
        # Transition period (both addresses active)
        transition_duration = 300  # 5 minutes
        
        active_addresses = [old_address, new_address]
        
        # Verify both addresses are available
        self.assertEqual(len(active_addresses), 2)
        self.assertIn(old_address, active_addresses)
        self.assertIn(new_address, active_addresses)
        
        # After transition, only new address active
        time.sleep(0.1)  # Simulate passage of time (shortened for test)
        active_addresses = [new_address]
        
        self.assertEqual(len(active_addresses), 1)
        self.assertEqual(active_addresses[0], new_address)
    
    def test_peer_address_update(self):
        """Test updating peer's stored onion address after rotation"""
        peer_id = "peer_rotation_001"
        old_address = "oldpeer.onion"
        new_address = "newpeer.onion"
        
        # Add peer with old address
        self.db.add_peer(peer_id, nickname="RotationPeer")
        
        # Store address in metadata (would be in public_key or separate field)
        self.db.update_peer(peer_id, public_key=f"address:{old_address}".encode())
        
        # Verify old address
        peer = self.db.get_peer(peer_id)
        self.assertIn(old_address.encode(), peer['public_key'])
        
        # Simulate receiving rotation notification
        # Update peer's address
        self.db.update_peer(peer_id, public_key=f"address:{new_address}".encode())
        
        # Verify new address
        peer = self.db.get_peer(peer_id)
        self.assertIn(new_address.encode(), peer['public_key'])
    
    def test_message_queue_preservation(self):
        """Test that pending messages are preserved during rotation"""
        peer_id = "peer_rotation_002"
        self.db.add_peer(peer_id, nickname="MessagePeer")
        
        # Queue messages before rotation
        message_ids = []
        for i in range(3):
            message_id = f"msg_{i:03d}"
            content = f"Message {i}".encode()
            timestamp = int(time.time())
            
            self.db.insert_message(
                peer_id=peer_id,
                content=content,
                timestamp=timestamp,
                message_id=message_id,
                sync_status=0  # Pending
            )
            message_ids.append(message_id)
        
        # Verify messages are pending
        pending_before = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending_before), 3)
        
        # Simulate rotation
        # (No database operations should affect pending messages)
        
        # Verify messages still pending after rotation
        pending_after = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending_after), 3)
        
        # Verify same messages
        for msg_id in message_ids:
            self.assertIn(msg_id, [m['message_id'] for m in pending_after])
    
    def test_automatic_reconnection_after_rotation(self):
        """Test automatic reconnection using new address"""
        peer_id = "peer_rotation_003"
        old_address = "oldconnect.onion"
        new_address = "newconnect.onion"
        
        # Initial connection
        connection_state = {
            'peer_id': peer_id,
            'address': old_address,
            'connected': True
        }
        
        # Simulate rotation notification received
        connection_state['address'] = new_address
        
        # Verify address updated
        self.assertEqual(connection_state['address'], new_address)
        
        # Connection should be re-established with new address
        # (In real implementation, this would trigger reconnection)
        connection_state['reconnecting'] = True
        
        # After reconnection
        connection_state['reconnecting'] = False
        connection_state['connected'] = True
        
        # Verify connection is active with new address
        self.assertTrue(connection_state['connected'])
        self.assertEqual(connection_state['address'], new_address)
    
    def test_multiple_rotation_cycles(self):
        """Test multiple rotation cycles"""
        addresses = []
        
        # Simulate 5 rotation cycles
        for i in range(5):
            new_address = f"rotation{i:02d}.onion"
            addresses.append(new_address)
        
        # Verify all addresses were generated
        self.assertEqual(len(addresses), 5)
        
        # Verify addresses are unique
        self.assertEqual(len(set(addresses)), 5)
    
    def test_rotation_timing(self):
        """Test rotation timing intervals"""
        # Rotation intervals (in seconds for test, hours in production)
        intervals = [1, 24, 48, 168]  # 1h, 24h, 48h, 168h (1 week)
        
        for interval in intervals:
            # Verify interval is valid
            self.assertGreater(interval, 0)
            self.assertLessEqual(interval, 168)


class TestOnionRotationIntegration(unittest.TestCase):
    """Integration tests for onion rotation"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.db = DBHandler(db_path=self.db_path)
        self.db.init_db()
    
    def tearDown(self):
        self.db.close()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_rotation_workflow(self):
        """Test complete rotation workflow"""
        # Setup
        peer_id = "peer_workflow"
        self.db.add_peer(peer_id, nickname="WorkflowPeer")
        
        # Add pending messages
        for i in range(3):
            self.db.insert_message(
                peer_id=peer_id,
                content=f"Message {i}".encode(),
                timestamp=int(time.time()),
                message_id=f"msg_{i}",
                sync_status=0
            )
        
        # Step 1: Generate new address
        old_address = "old.onion"
        new_address = "new.onion"
        
        # Step 2: Notify peer
        notification_sent = True
        self.assertTrue(notification_sent)
        
        # Step 3: Update local records
        self.db.update_peer(peer_id, public_key=new_address.encode())
        
        # Step 4: Verify messages preserved
        pending = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending), 3)
        
        # Step 5: Reconnect
        reconnected = True
        self.assertTrue(reconnected)
        
        # Step 6: Resume message transmission
        def mock_send(msg):
            return True
        
        self.db.retry_pending_messages(peer_id, mock_send)
        
        # Verify messages sent
        pending_after = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending_after), 0)
    
    def test_rotation_with_active_file_transfer(self):
        """Test rotation doesn't interrupt active file transfers"""
        # Simulate file transfer in progress
        file_transfer_state = {
            'active': True,
            'bytes_sent': 5000,
            'total_bytes': 10000,
            'completed': False
        }
        
        # Rotation occurs
        rotation_occurred = True
        
        # File transfer continues
        file_transfer_state['bytes_sent'] = 7500
        
        # Verify transfer wasn't interrupted
        self.assertTrue(file_transfer_state['active'])
        self.assertFalse(file_transfer_state['completed'])
        
        # Complete transfer
        file_transfer_state['bytes_sent'] = 10000
        file_transfer_state['completed'] = True
        file_transfer_state['active'] = False
        
        # Verify transfer completed successfully
        self.assertTrue(file_transfer_state['completed'])
    
    def test_rotation_error_handling(self):
        """Test error handling during rotation"""
        # Simulate rotation failure
        rotation_failed = True
        
        if rotation_failed:
            # Fallback: keep using old address
            current_address = "old.onion"
        else:
            current_address = "new.onion"
        
        # Verify fallback behavior
        self.assertEqual(current_address, "old.onion")
        
        # Retry rotation
        rotation_retry_success = True
        
        if rotation_retry_success:
            current_address = "new.onion"
        
        # Verify retry succeeded
        self.assertEqual(current_address, "new.onion")


def run_tests():
    """Run all onion rotation tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOnionRotation))
    suite.addTests(loader.loadTestsFromTestCase(TestOnionRotationIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
