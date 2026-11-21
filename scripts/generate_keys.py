"""
Key Generation Script for Road Quality Monitor
Generates:
1. Fernet symmetric key (AES-128 in CBC mode with HMAC-SHA256) for encrypting sensitive fields.
2. RSA 2048-bit key pair for digital signatures (authenticity & non-repudiation of accepted records).
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from config import KEYS_DIR, FERNET_KEY_FILE, RSA_PRIVATE_KEY_FILE, RSA_PUBLIC_KEY_FILE


def generate_fernet_key(force=False):
    """Generate and save a Fernet key for symmetric encryption."""
    key_path = Path(FERNET_KEY_FILE)
    if key_path.exists() and not force:
        print(f"[INFO] Fernet key already exists at: {key_path}")
        return

    key = Fernet.generate_key()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    with open(key_path, "wb") as f:
        f.write(key)
    print(f"[SUCCESS] Generated new Fernet symmetric key at: {key_path}")


def generate_rsa_keypair(force=False):
    """Generate and save an RSA 2048-bit private and public key pair."""
    priv_path = Path(RSA_PRIVATE_KEY_FILE)
    pub_path = Path(RSA_PUBLIC_KEY_FILE)

    if priv_path.exists() and pub_path.exists() and not force:
        print(f"[INFO] RSA keys already exist at: {priv_path} and {pub_path}")
        return

    # Generate 2048-bit RSA private key with public exponent 65537
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Serialize private key to PEM format
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Extract and serialize public key to PEM format
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    priv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(priv_path, "wb") as f:
        f.write(priv_pem)
    with open(pub_path, "wb") as f:
        f.write(pub_pem)

    print(f"[SUCCESS] Generated RSA private key at: {priv_path}")
    print(f"[SUCCESS] Generated RSA public key at: {pub_path}")


def main():
    force = "--force" in sys.argv
    print("=" * 60)
    print("RoadQualityMonitor Cryptographic Key Generator")
    print("=" * 60)
    generate_fernet_key(force=force)
    generate_rsa_keypair(force=force)
    print("=" * 60)
    print("Keys ready for encryption, decryption, and digital signatures.")
    print("=" * 60)


if __name__ == "__main__":
    main()
