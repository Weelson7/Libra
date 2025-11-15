"""
Device Linking Module for Libra
Handles device pairing, validation, and multi-device synchronization
"""
import re
import random
import hashlib
import time
import json
from typing import Optional, Dict, Tuple
from pathlib import Path

from data.word_dictionary import adjectives, verbs, nouns
from db.device_manager import DeviceManager
from utils.crypto_utils import generate_rsa_keypair, serialize_public_key, load_public_key
from config import DB_PATH


class DeviceLinking:
    """Main class for device linking and management"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DB_PATH)
        self.device_manager = DeviceManager(self.db_path)
        self.active_pairing_codes = {}  # code -> (device_info, expiry_time)
        
    def generate_pairing_code(self) -> str:
        """Generate a unique 3-word pairing code (adjective-verb-noun)"""
        code = f"{random.choice(adjectives)}-{random.choice(verbs)}-{random.choice(nouns)}"
        return code.lower()
    
    def create_pairing_request(self, device_name: str, user_id: str, 
                              expiry_seconds: int = 300) -> Tuple[str, Dict]:
        """
        Create a pairing request with temporary code
        
        Args:
            device_name: Name of device requesting pairing
            user_id: User ID for multi-device sync
            expiry_seconds: How long the code is valid (default 5 minutes)
            
        Returns:
            Tuple of (pairing_code, device_info_dict)
        """
        # Generate unique device ID
        device_id = self._generate_device_id(device_name, user_id)
        
        # Generate keypair for this device
        priv_key, pub_key = generate_rsa_keypair()
        pub_key_pem = serialize_public_key(pub_key).decode('utf-8')
        
        # Create pairing code
        pairing_code = self.generate_pairing_code()
        
        # Ensure unique code
        while pairing_code in self.active_pairing_codes:
            pairing_code = self.generate_pairing_code()
        
        # Store device info
        device_info = {
            'device_id': device_id,
            'device_name': device_name,
            'user_id': user_id,
            'public_key': pub_key_pem,
            'timestamp': int(time.time()),
            'expiry': int(time.time()) + expiry_seconds
        }
        
        self.active_pairing_codes[pairing_code] = device_info
        
        return pairing_code, device_info
    
    def accept_pairing(self, pairing_code: str, acceptor_user_id: str) -> bool:
        """
        Accept a pairing request from another device
        
        Args:
            pairing_code: The 3-word pairing code
            acceptor_user_id: User ID accepting the pairing
            
        Returns:
            True if pairing successful, False otherwise
        """
        pairing_code = pairing_code.lower().strip()
        
        # Check if code exists and is valid
        if pairing_code not in self.active_pairing_codes:
            raise ValueError("Invalid or expired pairing code")
        
        device_info = self.active_pairing_codes[pairing_code]
        
        # Check expiry
        if int(time.time()) > device_info['expiry']:
            del self.active_pairing_codes[pairing_code]
            raise ValueError("Pairing code has expired")
        
        # Verify user IDs match (for multi-device sync)
        if device_info['user_id'] != acceptor_user_id:
            raise ValueError("User ID mismatch - cannot pair devices from different users")
        
        # Link the device
        self.device_manager.link_device(
            device_id=device_info['device_id'],
            user_id=device_info['user_id'],
            device_key=device_info['public_key'],
            name=device_info['device_name'],
            trust_level=2  # Trusted device
        )
        
        # Remove code after successful pairing
        del self.active_pairing_codes[pairing_code]
        
        return True
    
    def get_linked_devices(self, user_id: str) -> list:
        """Get all devices linked to this user"""
        return self.device_manager.get_devices(user_id)
    
    def revoke_device(self, device_id: str) -> bool:
        """Revoke access for a linked device"""
        try:
            self.device_manager.revoke_device(device_id)
            return True
        except Exception as e:
            print(f"Error revoking device: {e}")
            return False
    
    def rename_device(self, device_id: str, new_name: str) -> bool:
        """Rename a linked device"""
        try:
            if not validate_device_name(new_name):
                raise ValueError("Invalid device name")
            self.device_manager.rename_device(device_id, new_name)
            return True
        except Exception as e:
            print(f"Error renaming device: {e}")
            return False
    
    def update_device_activity(self, device_id: str):
        """Update last active timestamp for device"""
        self.device_manager.update_last_active(device_id)
    
    def generate_qr_data(self, pairing_code: str) -> str:
        """
        Generate QR code data for device pairing
        
        Returns:
            JSON string with pairing information
        """
        if pairing_code not in self.active_pairing_codes:
            raise ValueError("Invalid pairing code")
        
        device_info = self.active_pairing_codes[pairing_code]
        
        qr_data = {
            'type': 'device_pairing',
            'code': pairing_code,
            'device_id': device_info['device_id'],
            'device_name': device_info['device_name'],
            'public_key': device_info['public_key'],
            'expiry': device_info['expiry']
        }
        
        return json.dumps(qr_data)
    
    def parse_qr_data(self, qr_json: str) -> Dict:
        """Parse QR code data for device pairing"""
        try:
            data = json.loads(qr_json)
            if data.get('type') != 'device_pairing':
                raise ValueError("Invalid QR code type")
            return data
        except json.JSONDecodeError:
            raise ValueError("Invalid QR code format")
    
    def cleanup_expired_codes(self):
        """Remove expired pairing codes"""
        current_time = int(time.time())
        expired = [code for code, info in self.active_pairing_codes.items() 
                  if current_time > info['expiry']]
        for code in expired:
            del self.active_pairing_codes[code]
    
    def _generate_device_id(self, device_name: str, user_id: str) -> str:
        """Generate unique device ID"""
        timestamp = str(time.time())
        data = f"{device_name}{user_id}{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()[:16]
    
    def close(self):
        """Close device manager connection"""
        self.device_manager.close()


# Validation functions
def validate_input(data: str, pattern: str) -> bool:
    """Validate input against a regex pattern"""
    return bool(re.match(pattern, data))


def validate_device_id(device_id: str) -> bool:
    """Validate device ID format"""
    return validate_input(device_id, r'^[a-zA-Z0-9_-]{4,32}$')


def validate_device_name(name: str) -> bool:
    """Validate device name"""
    return 2 <= len(name) <= 50 and validate_input(name, r'^[a-zA-Z0-9\s_-]+$')


def validate_pairing_code(code: str) -> bool:
    """Validate pairing code format (word-word-word)"""
    return validate_input(code, r'^[a-z]+-[a-z]+-[a-z]+$')


# Legacy function for backward compatibility
def generate_pairing_code() -> str:
    """Generate a 3-word pairing code (adjective-verb-noun)"""
    return f"{random.choice(adjectives)}-{random.choice(verbs)}-{random.choice(nouns)}".lower()


# Example usage and testing
if __name__ == "__main__":
    print("Device Linking Module Test")
    print("=" * 50)
    
    # Initialize device linking
    linker = DeviceLinking()
    
    # Test 1: Generate pairing code
    print("\n1. Generate Pairing Code:")
    code, device_info = linker.create_pairing_request(
        device_name="My Laptop",
        user_id="user123"
    )
    print(f"   Pairing Code: {code}")
    print(f"   Device ID: {device_info['device_id']}")
    print(f"   Expires: {device_info['expiry'] - int(time.time())} seconds")
    
    # Test 2: Generate QR data
    print("\n2. Generate QR Data:")
    qr_data = linker.generate_qr_data(code)
    print(f"   QR Data Length: {len(qr_data)} chars")
    print(f"   Preview: {qr_data[:100]}...")
    
    # Test 3: Accept pairing
    print("\n3. Accept Pairing:")
    try:
        success = linker.accept_pairing(code, "user123")
        print(f"   Pairing Success: {success}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: List devices
    print("\n4. List Linked Devices:")
    devices = linker.get_linked_devices("user123")
    for device in devices:
        print(f"   - {device['name']} ({device['device_id']})")
    
    # Cleanup
    linker.close()
    print("\n" + "=" * 50)
