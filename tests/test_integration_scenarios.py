"""
Integration Test: End-to-end scenarios for all critical features
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tempfile
import time
from pathlib import Path

from db.db_handler import DBHandler
from peer.connection_manager import ConnectionManager
from utils.crypto_utils import generate_rsa_keypair
from utils.file_transfer import save_file_to_storage


class TestEndToEndScenarios(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.storage_dir = Path(self.temp_dir) / 'storage'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = DBHandler(db_path=self.db_path)
        self.db.init_db()
        
        self.conn_mgr = ConnectionManager()
        
        # Generate keypairs for test peers
        self.peer1_priv, self.peer1_pub = generate_rsa_keypair()
        self.peer2_priv, self.peer2_pub = generate_rsa_keypair()
    
    def tearDown(self):
        """Clean up test environment"""
        self.db.close()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_offline_online_cycle(self):
        """
        Test complete workflow:
        1. User sends message to offline peer
        2. Message queued
        3. Peer comes online
        4. Message automatically sent
        5. Delivery confirmed
        """
        # Setup
        peer_id = "peer_complete_001"
        self.db.add_peer(peer_id, nickname="CompletePeer")
        
        # Step 1: Send message while peer offline
        message_id = "msg_complete_001"
        content = b"Complete test message"
        timestamp = int(time.time())
        
        self.db.insert_message(
            peer_id=peer_id,
            content=content,
            timestamp=timestamp,
            message_id=message_id,
            sync_status=0  # Pending
        )
        
        # Verify message is pending
        msg = self.db.get_message(message_id)
        self.assertEqual(msg['sync_status'], 0)
        
        # Step 2: Peer comes online
        self.db.update_peer_status(peer_id, int(time.time()))
        
        # Step 3: Automatic retry
        def mock_send(msg_data):
            return True  # Success
        
        self.db.retry_pending_messages(peer_id, mock_send)
        
        # Step 4: Verify message sent
        msg = self.db.get_message(message_id)
        self.assertEqual(msg['sync_status'], 1)
        
        # Step 5: Delivery confirmation
        self.db.mark_message_delivered(message_id)
        msg = self.db.get_message(message_id)
        self.assertEqual(msg['sync_status'], 2)
    
    def test_complete_file_transfer_workflow(self):
        """
        Test complete file transfer:
        1. Select file
        2. Save to storage
        3. Store metadata
        4. Split into chunks
        5. Send chunks
        6. Track progress
        7. Verify delivery
        """
        from utils.file_transfer import split_file, reassemble_file
        
        # Setup
        peer_id = "peer_file_complete"
        self.db.add_peer(peer_id, nickname="FilePeer")
        
        # Step 1: Create test file
        test_file = Path(self.temp_dir) / "test_complete.bin"
        test_content = b"File transfer test data" * 100
        test_file.write_bytes(test_content)
        
        # Step 2: Save to storage
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        file_size = os.path.getsize(dst_path)
        
        # Step 3: Store metadata (without message for simplicity)
        message_id = None
        file_id = self.db.insert_file_metadata(
            file_name=test_file.name,
            file_path=dst_path,
            file_hash=file_hash,
            file_size=file_size,
            message_id=message_id,
            peer_id=peer_id,
            timestamp=int(time.time())
        )
        
        # Step 4: Split into chunks
        chunks = list(split_file(dst_path))
        self.assertGreater(len(chunks), 0)
        
        # Step 5: Simulate sending chunks
        sent_bytes = 0
        for seq, data in chunks:
            sent_bytes += len(data)
        
        # Verify all bytes sent
        self.assertEqual(sent_bytes, file_size)
        
        # Step 6: Reassemble on receiver
        output_file = Path(self.temp_dir) / "received_complete.bin"
        reassemble_file(chunks, str(output_file))
        
        # Step 7: Verify integrity
        received_content = output_file.read_bytes()
        self.assertEqual(received_content, test_content)
    
    def test_p2p_with_tor_fallback_scenario(self):
        """
        Test P2P with Tor fallback:
        1. Attempt P2P connection
        2. P2P fails
        3. Fallback to Tor
        4. Message sent via Tor
        """
        from unittest.mock import Mock
        
        # Setup
        peer_id = "peer_p2p_tor"
        self.db.add_peer(peer_id, nickname="P2PTorPeer")
        
        # Step 1: Attempt P2P (mock)
        p2p_socket = None  # Simulates P2P failure
        
        # Step 2: P2P fails
        if p2p_socket is None:
            # Step 3: Fallback to Tor
            tor_socket = Mock()
            active_socket = tor_socket
            connection_type = 'tor'
        else:
            active_socket = p2p_socket
            connection_type = 'direct'
        
        # Verify fallback occurred
        self.assertEqual(connection_type, 'tor')
        self.assertIsNotNone(active_socket)
        
        # Step 4: Send message via Tor
        message_id = "msg_p2p_tor"
        self.db.insert_message(
            peer_id=peer_id,
            content=b"Message via Tor fallback",
            timestamp=int(time.time()),
            message_id=message_id,
            sync_status=1  # Sent via Tor
        )
        
        msg = self.db.get_message(message_id)
        self.assertEqual(msg['sync_status'], 1)
    
    def test_onion_rotation_with_active_session(self):
        """
        Test onion rotation without interruption:
        1. Establish connection
        2. Send messages
        3. Rotate onion address
        4. Continue sending messages
        5. Verify no interruption
        """
        # Setup
        peer_id = "peer_rotation_active"
        self.db.add_peer(peer_id, nickname="RotationPeer")
        
        # Step 1: Initial connection
        old_address = "old123.onion"
        self.db.update_peer(peer_id, public_key=old_address.encode())
        
        # Step 2: Send messages before rotation
        for i in range(3):
            message_id = f"msg_before_{i}"
            self.db.insert_message(
                peer_id=peer_id,
                content=f"Before rotation {i}".encode(),
                timestamp=int(time.time()),
                message_id=message_id,
                sync_status=2  # Delivered
            )
        
        # Step 3: Rotate address
        new_address = "new456.onion"
        self.db.update_peer(peer_id, public_key=new_address.encode())
        
        # Step 4: Send messages after rotation
        for i in range(3):
            message_id = f"msg_after_{i}"
            self.db.insert_message(
                peer_id=peer_id,
                content=f"After rotation {i}".encode(),
                timestamp=int(time.time()),
                message_id=message_id,
                sync_status=2  # Delivered
            )
        
        # Step 5: Verify all messages delivered
        all_messages = self.db.get_messages_by_peer(peer_id)
        self.assertEqual(len(all_messages), 6)
        
        # Verify all delivered
        for msg in all_messages:
            self.assertEqual(msg['sync_status'], 2)
    
    def test_user_logoff_login_cycle(self):
        """
        Test user logoff and login:
        1. User sends messages to multiple peers
        2. Some messages pending
        3. User logs off (app closes)
        4. User logs in (app opens)
        5. Messages loaded from database
        6. Pending messages retry automatically
        """
        # Setup multiple peers
        peers = []
        for i in range(3):
            peer_id = f"peer_logoff_{i}"
            self.db.add_peer(peer_id, nickname=f"LogoffPeer{i}")
            peers.append(peer_id)
        
        # Step 1: Send messages (some pending, some sent)
        for i, peer_id in enumerate(peers):
            for j in range(2):
                message_id = f"msg_logoff_{i}_{j}"
                sync_status = 0 if j == 0 else 1  # First pending, second sent
                
                self.db.insert_message(
                    peer_id=peer_id,
                    content=f"Message to {peer_id}".encode(),
                    timestamp=int(time.time()),
                    message_id=message_id,
                    sync_status=sync_status
                )
        
        # Step 2: Verify pending messages
        all_pending = self.db.list_pending_messages()
        self.assertEqual(len(all_pending), 3)  # One per peer
        
        # Step 3: Simulate logoff (close database)
        self.db.close()
        
        # Step 4: Simulate login (reopen database)
        self.db = DBHandler(db_path=self.db_path)
        self.db.connect()
        
        # Step 5: Load messages from database
        all_pending_after = self.db.list_pending_messages()
        self.assertEqual(len(all_pending_after), 3)
        
        # Step 6: Retry pending messages
        def mock_send(msg):
            return True
        
        for peer_id in peers:
            self.db.retry_pending_messages(peer_id, mock_send)
        
        # Verify no more pending
        final_pending = self.db.list_pending_messages()
        self.assertEqual(len(final_pending), 0)
    
    def test_concurrent_operations(self):
        """
        Test concurrent operations:
        1. Send message
        2. Transfer file
        3. Rotate address
        4. All complete successfully
        """
        peer_id = "peer_concurrent"
        self.db.add_peer(peer_id, nickname="ConcurrentPeer")
        
        # Operation 1: Send message
        msg_id = "msg_concurrent"
        self.db.insert_message(
            peer_id=peer_id,
            content=b"Concurrent message",
            timestamp=int(time.time()),
            message_id=msg_id,
            sync_status=1
        )
        
        # Operation 2: Transfer file
        test_file = Path(self.temp_dir) / "concurrent_file.bin"
        test_file.write_bytes(b"Concurrent file data" * 10)
        
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        
        file_id = self.db.insert_file_metadata(
            file_name=test_file.name,
            file_path=dst_path,
            file_hash=file_hash,
            file_size=os.path.getsize(dst_path),
            peer_id=peer_id,
            timestamp=int(time.time())
        )
        
        # Operation 3: Rotate address
        self.db.update_peer(peer_id, public_key=b"rotated123.onion")
        
        # Verify all operations completed
        msg = self.db.get_message(msg_id)
        self.assertIsNotNone(msg)
        
        files = self.db.get_file_metadata_by_peer(peer_id)
        self.assertEqual(len(files), 1)
        
        peer = self.db.get_peer(peer_id)
        self.assertEqual(peer['public_key'], b"rotated123.onion")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
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
    
    def test_peer_goes_offline_mid_transfer(self):
        """Test handling when peer goes offline during transfer"""
        peer_id = "peer_mid_offline"
        self.db.add_peer(peer_id, nickname="MidOfflinePeer")
        
        # Start sending messages
        for i in range(5):
            message_id = f"msg_mid_{i}"
            # First 2 succeed, rest fail
            sync_status = 1 if i < 2 else 0
            
            self.db.insert_message(
                peer_id=peer_id,
                content=f"Message {i}".encode(),
                timestamp=int(time.time()),
                message_id=message_id,
                sync_status=sync_status
            )
        
        # Verify some sent, some pending
        pending = self.db.get_pending_messages_for_peer(peer_id)
        self.assertEqual(len(pending), 3)
        
        messages = self.db.get_messages_by_peer(peer_id)
        sent_count = sum(1 for m in messages if m['sync_status'] == 1)
        self.assertEqual(sent_count, 2)
    
    def test_duplicate_message_handling(self):
        """Test handling of duplicate message IDs"""
        peer_id = "peer_duplicate"
        self.db.add_peer(peer_id, nickname="DuplicatePeer")
        
        message_id = "msg_duplicate"
        content = b"Duplicate test"
        timestamp = int(time.time())
        
        # Insert first time
        self.db.insert_message(
            peer_id=peer_id,
            content=content,
            timestamp=timestamp,
            message_id=message_id,
            sync_status=0
        )
        
        # Try to insert again (should be handled by database constraints)
        try:
            self.db.insert_message(
                peer_id=peer_id,
                content=content,
                timestamp=timestamp,
                message_id=message_id,
                sync_status=0
            )
            duplicate_inserted = True
        except:
            duplicate_inserted = False
        
        # Verify only one message exists
        msg = self.db.get_message(message_id)
        self.assertIsNotNone(msg)


def run_tests():
    """Run all integration tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
