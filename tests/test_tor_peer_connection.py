import pytest
import msgpack
import io
from unittest.mock import Mock, MagicMock
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.crypto_utils import generate_rsa_keypair, serialize_public_key, hybrid_encrypt, hybrid_decrypt

# Mock-based test for Tor peer connection that validates secure rendezvous logic
# without requiring a running Tor instance

class TestTorPeerConnection:
    def test_secure_rendezvous_encryption_decryption(self):
        """Test that rendezvous payloads are correctly encrypted and decrypted using hybrid encryption."""
        # Generate keypairs for two peers
        priv1, pub1 = generate_rsa_keypair()
        priv2, pub2 = generate_rsa_keypair()
        
        # Serialize public keys
        pub1_pem = serialize_public_key(pub1)
        pub2_pem = serialize_public_key(pub2)
        
        # Prepare rendezvous payload from peer 1 to peer 2
        session_info = {"session_id": "abc123", "timestamp": 1234567890}
        nat_info = {"nat_type": "symmetric", "external_ip": "1.2.3.4", "external_port": 12345}
        
        payload = {
            "type": "rendezvous",
            "public_key": pub1_pem.decode('utf-8'),
            "session_info": session_info,
            "nat_info": nat_info
        }
        
        # Pack with msgpack
        packed = msgpack.packb(payload)
        
        # Encrypt with peer 2's public key (peer 1 sends to peer 2)
        encrypted = hybrid_encrypt(pub2, packed)
        
        # Peer 2 decrypts with their private key
        decrypted = hybrid_decrypt(priv2, encrypted)
        
        # Unpack and verify
        received_payload = msgpack.unpackb(decrypted, raw=False)
        
        assert received_payload["type"] == "rendezvous"
        assert received_payload["session_info"]["session_id"] == "abc123"
        assert received_payload["nat_info"]["nat_type"] == "symmetric"
        assert received_payload["nat_info"]["external_port"] == 12345
    
    def test_bidirectional_rendezvous_exchange(self):
        """Test bidirectional secure rendezvous exchange between two peers."""
        # Generate keypairs for two peers
        priv1, pub1 = generate_rsa_keypair()
        priv2, pub2 = generate_rsa_keypair()
        
        pub1_pem = serialize_public_key(pub1)
        pub2_pem = serialize_public_key(pub2)
        
        # Peer 1 sends rendezvous to Peer 2
        payload1 = {
            "type": "rendezvous",
            "public_key": pub1_pem.decode('utf-8'),
            "session_info": {"session_id": "peer1_session", "peer_id": "peer1"},
            "nat_info": {"nat_type": "cone", "port": 8001}
        }
        packed1 = msgpack.packb(payload1)
        encrypted1 = hybrid_encrypt(pub2, packed1)
        decrypted1 = hybrid_decrypt(priv2, encrypted1)
        received1 = msgpack.unpackb(decrypted1, raw=False)
        
        # Peer 2 sends rendezvous to Peer 1
        payload2 = {
            "type": "rendezvous",
            "public_key": pub2_pem.decode('utf-8'),
            "session_info": {"session_id": "peer2_session", "peer_id": "peer2"},
            "nat_info": {"nat_type": "symmetric", "port": 8002}
        }
        packed2 = msgpack.packb(payload2)
        encrypted2 = hybrid_encrypt(pub1, packed2)
        decrypted2 = hybrid_decrypt(priv1, encrypted2)
        received2 = msgpack.unpackb(decrypted2, raw=False)
        
        # Verify both peers received correct information
        assert received1["session_info"]["peer_id"] == "peer1"
        assert received1["nat_info"]["port"] == 8001
        assert received2["session_info"]["peer_id"] == "peer2"
        assert received2["nat_info"]["port"] == 8002
    
    def test_rendezvous_with_authentication(self):
        """Test that rendezvous messages include proper authentication data."""
        from utils.crypto_utils import sign_message, verify_signature
        
        priv1, pub1 = generate_rsa_keypair()
        priv2, pub2 = generate_rsa_keypair()
        
        pub2_pem = serialize_public_key(pub2)
        
        # Create payload with signature
        payload = {
            "type": "rendezvous",
            "public_key": serialize_public_key(pub1).decode('utf-8'),
            "session_info": {"session_id": "signed_session"},
            "nat_info": {"nat_type": "restricted"}
        }
        packed = msgpack.packb(payload)
        
        # Sign the packed payload
        signature = sign_message(priv1, packed)
        
        # Create authenticated message
        auth_message = {
            "payload": packed,
            "signature": signature
        }
        auth_packed = msgpack.packb(auth_message)
        
        # Encrypt and send
        encrypted = hybrid_encrypt(pub2, auth_packed)
        decrypted = hybrid_decrypt(priv2, encrypted)
        
        # Verify on receiver side
        received_auth = msgpack.unpackb(decrypted, raw=False)
        received_payload_packed = received_auth["payload"]
        received_signature = received_auth["signature"]
        
        # Verify signature with peer 1's public key
        assert verify_signature(pub1, received_payload_packed, received_signature)
        
        # Unpack the actual payload
        received_payload = msgpack.unpackb(received_payload_packed, raw=False)
        assert received_payload["type"] == "rendezvous"
        assert received_payload["session_info"]["session_id"] == "signed_session"
