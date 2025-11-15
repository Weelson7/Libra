"""
Test: File attachments are sent and received properly
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import tempfile
import hashlib
from pathlib import Path

from db.db_handler import DBHandler
from utils.file_transfer import save_file_to_storage, split_file, reassemble_file
from peer.connection_manager import ConnectionManager


class TestFileTransfer(unittest.TestCase):
    """Test file transfer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / 'storage'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
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
    
    def create_test_file(self, size_bytes, content=None):
        """Create a test file with specified size"""
        test_file = Path(self.temp_dir) / f"test_file_{size_bytes}.bin"
        
        if content:
            test_file.write_bytes(content)
        else:
            # Fill with random data
            import random
            data = bytes([random.randint(0, 255) for _ in range(size_bytes)])
            test_file.write_bytes(data)
        
        return test_file
    
    def test_file_storage(self):
        """Test saving file to storage"""
        # Create test file
        test_file = self.create_test_file(1024, b"Test content" * 100)
        
        # Save to storage
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        
        # Verify file was saved
        self.assertTrue(os.path.exists(dst_path))
        
        # Verify hash
        with open(dst_path, 'rb') as f:
            data = f.read()
            computed_hash = hashlib.sha256(data).hexdigest()
            self.assertEqual(computed_hash, file_hash)
    
    def test_file_metadata_storage(self):
        """Test storing file metadata in database"""
        # Create test file
        test_file = self.create_test_file(2048)
        
        # Save to storage
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        file_size = os.path.getsize(dst_path)
        
        # Store metadata
        peer_id = "peer_file_001"
        message_id = None  # No message association
        timestamp = 1234567890
        
        # Add peer first to satisfy foreign key
        self.db.add_peer(peer_id, nickname="FilePeer")
        
        file_id = self.db.insert_file_metadata(
            file_name=test_file.name,
            file_path=dst_path,
            file_hash=file_hash,
            file_size=file_size,
            message_id=message_id,
            peer_id=peer_id,
            timestamp=timestamp
        )
        
        # Verify metadata was stored
        self.assertIsNotNone(file_id)
        
        # Retrieve metadata by peer
        files = self.db.get_file_metadata_by_peer(peer_id)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['file_name'], test_file.name)
        self.assertEqual(files[0]['file_hash'], file_hash)
    
    def test_file_chunking(self):
        """Test splitting file into chunks"""
        # Create test file
        test_content = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 1000
        test_file = self.create_test_file(len(test_content), test_content)
        
        # Split into chunks
        chunks = list(split_file(str(test_file)))
        
        # Verify chunks
        self.assertGreater(len(chunks), 0)
        
        # Verify chunk structure (seq, data)
        for seq, data in chunks:
            self.assertIsInstance(seq, int)
            self.assertIsInstance(data, bytes)
        
        # Verify all data is present
        reassembled = b''.join(data for seq, data in chunks)
        self.assertEqual(reassembled, test_content)
    
    def test_file_reassembly(self):
        """Test reassembling file from chunks"""
        # Create test file
        test_content = b"The quick brown fox jumps over the lazy dog." * 500
        test_file = self.create_test_file(len(test_content), test_content)
        
        # Split into chunks
        chunks = list(split_file(str(test_file)))
        
        # Reassemble
        output_file = Path(self.temp_dir) / "reassembled.bin"
        reassemble_file(chunks, str(output_file))
        
        # Verify reassembled file matches original
        reassembled_content = output_file.read_bytes()
        self.assertEqual(reassembled_content, test_content)
    
    def test_file_transfer_progress(self):
        """Test file transfer progress tracking"""
        # Create test file
        test_file = self.create_test_file(10240)  # 10KB
        file_size = os.path.getsize(test_file)
        
        # Track progress
        progress_updates = []
        
        def progress_callback(sent, total):
            progress_updates.append((sent, total))
        
        # Simulate chunked transfer
        chunks = list(split_file(str(test_file)))
        sent = 0
        for seq, data in chunks:
            sent += len(data)
            progress_callback(sent, file_size)
        
        # Verify progress was tracked
        self.assertGreater(len(progress_updates), 0)
        
        # Verify final progress
        final_sent, final_total = progress_updates[-1]
        self.assertEqual(final_sent, file_size)
        self.assertEqual(final_total, file_size)
    
    def test_large_file_transfer(self):
        """Test transfer of large file (1MB)"""
        # Create large test file
        test_file = self.create_test_file(1024 * 1024)  # 1MB
        
        # Split into chunks
        chunks = list(split_file(str(test_file)))
        
        # Verify reasonable number of chunks
        expected_chunks = (1024 * 1024) // (64 * 1024) + (1 if (1024 * 1024) % (64 * 1024) else 0)
        self.assertEqual(len(chunks), expected_chunks)
        
        # Reassemble
        output_file = Path(self.temp_dir) / "large_reassembled.bin"
        reassemble_file(chunks, str(output_file))
        
        # Verify sizes match
        original_size = os.path.getsize(test_file)
        reassembled_size = os.path.getsize(output_file)
        self.assertEqual(reassembled_size, original_size)
    
    def test_file_hash_verification(self):
        """Test file integrity verification via hash"""
        # Create test file
        test_content = b"Integrity test content" * 100
        test_file = self.create_test_file(len(test_content), test_content)
        
        # Save to storage
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        
        # Verify hash
        with open(dst_path, 'rb') as f:
            data = f.read()
            computed_hash = hashlib.sha256(data).hexdigest()
            self.assertEqual(computed_hash, file_hash)
        
        # Simulate corruption
        with open(dst_path, 'ab') as f:
            f.write(b'CORRUPT')
        
        # Verify hash no longer matches
        with open(dst_path, 'rb') as f:
            data = f.read()
            corrupted_hash = hashlib.sha256(data).hexdigest()
            self.assertNotEqual(corrupted_hash, file_hash)
    
    def test_multiple_file_transfers(self):
        """Test sending multiple files to same peer"""
        peer_id = "peer_multi_file"
        
        # Add peer first
        self.db.add_peer(peer_id, nickname="MultiFilePeer")
        
        # Send multiple files
        file_hashes = []
        for i in range(5):
            test_file = self.create_test_file(512 * (i + 1))
            dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
            file_size = os.path.getsize(dst_path)
            
            self.db.insert_file_metadata(
                file_name=test_file.name,
                file_path=dst_path,
                file_hash=file_hash,
                file_size=file_size,
                peer_id=peer_id,
                timestamp=1234567890 + i
            )
            
            file_hashes.append(file_hash)
        
        # Retrieve all files for peer
        files = self.db.get_file_metadata_by_peer(peer_id)
        self.assertEqual(len(files), 5)
        
        # Verify all hashes present
        retrieved_hashes = [f['file_hash'] for f in files]
        for h in file_hashes:
            self.assertIn(h, retrieved_hashes)
    
    def test_file_transfer_with_message(self):
        """Test file transfer associated with message"""
        peer_id = "peer_with_msg"
        message_id = "msg_with_file"
        
        # Add peer first
        self.db.add_peer(peer_id, nickname="MsgPeer")
        
        # Create message FIRST (foreign key requirement)
        self.db.insert_message(
            peer_id=peer_id,
            content=b"File attachment message",
            timestamp=1234567890,
            message_id=message_id,
            sync_status=0
        )
        
        # Create and save file
        test_file = self.create_test_file(2048)
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        file_size = os.path.getsize(dst_path)
        
        # Store file metadata with message ID
        self.db.insert_file_metadata(
            file_name=test_file.name,
            file_path=dst_path,
            file_hash=file_hash,
            file_size=file_size,
            message_id=message_id,
            peer_id=peer_id,
            timestamp=1234567890
        )
        
        # Retrieve file by message ID
        files = self.db.get_file_metadata_by_message(message_id)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]['file_hash'], file_hash)
        
        # Retrieve message
        msg = self.db.get_message(message_id)
        self.assertIsNotNone(msg)
        self.assertIn(b'File attachment', msg['content'])


class TestFileTransferEdgeCases(unittest.TestCase):
    """Test edge cases in file transfer"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / 'storage'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_empty_file_transfer(self):
        """Test transfer of empty file"""
        # Create empty file
        test_file = Path(self.temp_dir) / "empty.txt"
        test_file.write_bytes(b'')
        
        # Save to storage
        dst_path, file_hash = save_file_to_storage(str(test_file), str(self.storage_dir))
        
        # Verify file exists
        self.assertTrue(os.path.exists(dst_path))
        
        # Verify size is 0
        self.assertEqual(os.path.getsize(dst_path), 0)
    
    def test_single_byte_file(self):
        """Test transfer of single byte file"""
        test_file = Path(self.temp_dir) / "single.txt"
        test_file.write_bytes(b'X')
        
        # Split into chunks
        chunks = list(split_file(str(test_file)))
        
        # Should have 1 chunk
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0][1], b'X')
    
    def test_exact_chunk_size_file(self):
        """Test file that's exactly chunk size"""
        chunk_size = 1024
        test_file = Path(self.temp_dir) / "exact.bin"
        test_file.write_bytes(b'A' * chunk_size)
        
        # Split into chunks
        chunks = list(split_file(str(test_file)))
        
        # Should have exactly 1 chunk
        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(chunks[0][1]), chunk_size)


def run_tests():
    """Run all file transfer tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFileTransfer))
    suite.addTests(loader.loadTestsFromTestCase(TestFileTransferEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
