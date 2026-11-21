"""
Automated Unit Tests for Cryptography and Security Features
Tests:
1. Fernet symmetric encryption and decryption.
2. SHA-256 canonical hashing and integrity verification.
3. RSA-2048 keypair digital signatures and public-key verification.
4. Tamper detection: modifying data invalidates both SHA-256 and RSA signatures.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import crypto_utils


class TestCryptoUtils(unittest.TestCase):

    def setUp(self):
        crypto_utils._ensure_keys_exist()

    def test_fernet_encryption_and_decryption(self):
        """Test symmetric encryption and decryption of sensitive GPS data."""
        secret_coord = "12.971598,77.594562"
        encrypted = crypto_utils.encrypt_value(secret_coord)

        # Ciphertext must not match plaintext and must be non-empty
        self.assertNotEqual(secret_coord, encrypted)
        self.assertTrue(len(encrypted) > 20)

        # Decryption must restore exact original plaintext
        decrypted = crypto_utils.decrypt_value(encrypted)
        self.assertEqual(secret_coord, decrypted)

    def test_sha256_canonical_hashing(self):
        """Test deterministic canonical JSON representation and SHA-256 digest."""
        record_a = {
            "device_id": "DEV-TEST-01",
            "timestamp": "2026-10-12T10:00:00Z",
            "latitude": 12.9279,
            "longitude": 77.6835,
            "event_type": "Pothole",
            "confidence": 0.95,
            "pdi_score": 85.0
        }
        canonical_str = crypto_utils.build_canonical_string(record_a)
        hash_digest = crypto_utils.compute_sha256(canonical_str)

        # SHA-256 hex digest is exactly 64 characters
        self.assertEqual(len(hash_digest), 64)

        # Hash verification succeeds on original record
        self.assertTrue(crypto_utils.verify_sha256(canonical_str, hash_digest))

    def test_sha256_tamper_detection(self):
        """Test that altering any record field causes SHA-256 verification failure."""
        record = {
            "device_id": "DEV-TEST-01",
            "timestamp": "2026-10-12T10:00:00Z",
            "latitude": 12.9279,
            "longitude": 77.6835,
            "event_type": "Pothole",
            "confidence": 0.95,
            "pdi_score": 85.0
        }
        canonical_str = crypto_utils.build_canonical_string(record)
        original_hash = crypto_utils.compute_sha256(canonical_str)

        # Adversary alters pdi_score from 85.0 to 10.0
        tampered_record = dict(record)
        tampered_record["pdi_score"] = 10.0
        tampered_canonical = crypto_utils.build_canonical_string(tampered_record)

        # Verification must FAIL
        self.assertFalse(crypto_utils.verify_sha256(tampered_canonical, original_hash))

    def test_rsa_digital_signature_verification(self):
        """Test RSA private key signing and public key signature verification."""
        message = "CanonicalRecordPayload_Timestamp_12345"
        sig_b64 = crypto_utils.sign_data(message)

        # Signature must be base64 string
        self.assertTrue(len(sig_b64) > 100)

        # Verification using public key must succeed
        self.assertTrue(crypto_utils.verify_signature(message, sig_b64))

    def test_rsa_signature_tamper_detection(self):
        """Test that modifying signed payload causes RSA signature verification to fail."""
        message = "CanonicalRecordPayload_Genuine"
        sig_b64 = crypto_utils.sign_data(message)

        tampered_message = "CanonicalRecordPayload_Tampered"
        # Verification on tampered content must FAIL
        self.assertFalse(crypto_utils.verify_signature(tampered_message, sig_b64))


if __name__ == "__main__":
    unittest.main()
