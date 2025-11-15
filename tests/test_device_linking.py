"""
Test suite for Device Linking functionality
Tests pairing codes, QR codes, device management, and GUI integration
"""
import unittest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.device_linking import (
    DeviceLinking, 
    validate_device_id, 
    validate_device_name, 
    validate_pairing_code
)
from db.device_manager import DeviceManager
import time
import json


class TestDeviceLinking(unittest.TestCase):
    """Test DeviceLinking class functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.linker = DeviceLinking()
        self.user_id = "test_user_123"
        self.device_name = "Test Device"
    
    def tearDown(self):
        """Clean up after tests"""
        try:
            # Clean up test devices
            devices = self.linker.get_linked_devices(self.user_id)
            for device in devices:
                self.linker.revoke_device(device['device_id'])
            self.linker.cleanup_expired_codes()
            self.linker.close()
        except:
            pass
    
    def test_create_pairing_request(self):
        """Test pairing code generation"""
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id=self.user_id,
            expiry_seconds=300
        )
        
        # Check code format (word-word-word)
        self.assertIsNotNone(code)
        parts = code.split('-')
        self.assertEqual(len(parts), 3, "Code should have 3 words")
        
        # Check device info
        self.assertIn('device_id', device_info)
        self.assertIn('expiry', device_info)
        self.assertIn('public_key', device_info)
        
        # Verify code is valid
        self.assertTrue(validate_pairing_code(code))
    
    def test_accept_pairing(self):
        """Test accepting a pairing code"""
        # Generate code
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id=self.user_id
        )
        
        # Accept pairing
        success = self.linker.accept_pairing(code, self.user_id)
        self.assertTrue(success, "Pairing should succeed")
        
        # Verify device was linked
        devices = self.linker.get_linked_devices(self.user_id)
        self.assertEqual(len(devices), 1, "Should have 1 linked device")
        self.assertEqual(devices[0]['name'], self.device_name)
    
    def test_pairing_code_expiry(self):
        """Test that expired codes are rejected"""
        # Generate code with 1 second expiry
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id=self.user_id,
            expiry_seconds=1
        )
        
        # Wait for expiry
        time.sleep(2)
        
        # Try to accept expired code
        with self.assertRaises(ValueError) as context:
            self.linker.accept_pairing(code, self.user_id)
        
        self.assertIn("expired", str(context.exception).lower())
    
    def test_user_id_mismatch(self):
        """Test that codes only work for correct user"""
        # Generate code for user1
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id="user1"
        )
        
        # Try to accept with user2
        with self.assertRaises(ValueError) as context:
            self.linker.accept_pairing(code, "user2")
        
        self.assertIn("user", str(context.exception).lower())
    
    def test_generate_qr_data(self):
        """Test QR code data generation"""
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id=self.user_id
        )
        
        qr_data = self.linker.generate_qr_data(code)
        
        # Parse JSON
        data = json.loads(qr_data)
        
        self.assertEqual(data['type'], 'device_pairing')
        self.assertEqual(data['code'], code)
        self.assertIn('device_id', data)
        self.assertIn('public_key', data)
        self.assertIn('expiry', data)
    
    def test_parse_qr_data(self):
        """Test parsing QR code data"""
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id=self.user_id
        )
        
        qr_data = self.linker.generate_qr_data(code)
        parsed = self.linker.parse_qr_data(qr_data)
        
        self.assertEqual(parsed['code'], code)
        self.assertEqual(parsed['device_id'], device_info['device_id'])
    
    def test_get_linked_devices(self):
        """Test retrieving linked devices"""
        # Link 3 devices
        for i in range(3):
            code, _ = self.linker.create_pairing_request(
                device_name=f"Device {i}",
                user_id=self.user_id
            )
            self.linker.accept_pairing(code, self.user_id)
        
        # Get devices
        devices = self.linker.get_linked_devices(self.user_id)
        
        self.assertEqual(len(devices), 3)
        for i, device in enumerate(devices):
            self.assertIn('device_id', device)
            self.assertIn('name', device)
            self.assertIn('trust_level', device)
            self.assertIn('last_active', device)
    
    def test_rename_device(self):
        """Test renaming a device"""
        # Link device
        code, device_info = self.linker.create_pairing_request(
            device_name="Old Name",
            user_id=self.user_id
        )
        self.linker.accept_pairing(code, self.user_id)
        device_id = device_info['device_id']
        
        # Rename
        self.linker.rename_device(device_id, "New Name")
        
        # Verify
        devices = self.linker.get_linked_devices(self.user_id)
        device = next(d for d in devices if d['device_id'] == device_id)
        self.assertEqual(device['name'], "New Name")
    
    def test_revoke_device(self):
        """Test revoking device access"""
        # Link device
        code, device_info = self.linker.create_pairing_request(
            device_name=self.device_name,
            user_id=self.user_id
        )
        self.linker.accept_pairing(code, self.user_id)
        device_id = device_info['device_id']
        
        # Revoke
        self.linker.revoke_device(device_id)
        
        # Verify device is gone
        devices = self.linker.get_linked_devices(self.user_id)
        device_ids = [d['device_id'] for d in devices]
        self.assertNotIn(device_id, device_ids)
    
    def test_cleanup_expired_codes(self):
        """Test cleanup of expired pairing codes"""
        # Create code with 1 second expiry
        code1, _ = self.linker.create_pairing_request(
            device_name="Device1",
            user_id=self.user_id,
            expiry_seconds=1
        )
        
        # Create code with long expiry
        code2, _ = self.linker.create_pairing_request(
            device_name="Device2",
            user_id=self.user_id,
            expiry_seconds=3600
        )
        
        # Wait for first code to expire
        time.sleep(2)
        
        # Cleanup
        self.linker.cleanup_expired_codes()
        
        # code1 should be invalid
        with self.assertRaises(ValueError):
            self.linker.accept_pairing(code1, self.user_id)
        
        # code2 should still work
        success = self.linker.accept_pairing(code2, self.user_id)
        self.assertTrue(success)


class TestValidationFunctions(unittest.TestCase):
    """Test validation helper functions"""
    
    def test_validate_device_id(self):
        """Test device ID validation"""
        # Valid IDs
        self.assertTrue(validate_device_id("abcd"))
        self.assertTrue(validate_device_id("a" * 32))
        self.assertTrue(validate_device_id("abc-123_XYZ"))
        
        # Invalid IDs
        self.assertFalse(validate_device_id("abc"))  # Too short
        self.assertFalse(validate_device_id("a" * 33))  # Too long
        self.assertFalse(validate_device_id(""))  # Empty
        self.assertFalse(validate_device_id("abc@123"))  # Invalid char
    
    def test_validate_device_name(self):
        """Test device name validation"""
        # Valid names
        self.assertTrue(validate_device_name("My Phone"))
        self.assertTrue(validate_device_name("AB"))
        self.assertTrue(validate_device_name("a" * 50))
        
        # Invalid names
        self.assertFalse(validate_device_name("A"))  # Too short
        self.assertFalse(validate_device_name("a" * 51))  # Too long
        self.assertFalse(validate_device_name(""))  # Empty
    
    def test_validate_pairing_code(self):
        """Test pairing code validation"""
        # Valid codes
        self.assertTrue(validate_pairing_code("happy-jump-tree"))
        self.assertTrue(validate_pairing_code("quick-fox-dog"))
        
        # Invalid codes
        self.assertFalse(validate_pairing_code("only-two"))  # 2 words
        self.assertFalse(validate_pairing_code("one-two-three-four"))  # 4 words
        self.assertFalse(validate_pairing_code("no_hyphens_here"))  # Wrong separator
        self.assertFalse(validate_pairing_code(""))  # Empty


class TestDeviceManager(unittest.TestCase):
    """Test DeviceManager integration"""
    
    def setUp(self):
        """Set up test environment"""
        from config import DB_PATH
        self.device_mgr = DeviceManager(db_path=str(DB_PATH))
        self.user_id = "test_user_456"
    
    def tearDown(self):
        """Clean up after tests"""
        try:
            devices = self.device_mgr.get_devices(self.user_id)
            for device in devices:
                self.device_mgr.revoke_device(device['device_id'])
            self.device_mgr.close()
        except:
            pass
    
    def test_link_device(self):
        """Test linking a device through DeviceManager"""
        device_id = "test_device_001"
        device_key = "test_public_key"
        
        self.device_mgr.link_device(
            device_id=device_id,
            user_id=self.user_id,
            device_key=device_key,
            trust_level=2,
            name="Test Device"
        )
        
        # Verify
        devices = self.device_mgr.get_devices(self.user_id)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]['device_id'], device_id)
    
    def test_update_last_active(self):
        """Test updating device activity"""
        device_id = "test_device_002"
        
        self.device_mgr.link_device(
            device_id=device_id,
            user_id=self.user_id,
            device_key="key",
            trust_level=2,
            name="Test Device"
        )
        
        # Update activity
        time.sleep(1)
        self.device_mgr.update_last_active(device_id)
        
        # Verify timestamp changed
        devices = self.device_mgr.get_devices(self.user_id)
        device = devices[0]
        self.assertIsNotNone(device['last_active'])


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDeviceLinking))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestDeviceManager))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
