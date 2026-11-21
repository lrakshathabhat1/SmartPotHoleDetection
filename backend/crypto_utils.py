"""
Cryptographic Utilities Module
Implements:
1. SHA-256 Hashing: For record integrity verification and tamper detection.
2. Fernet Symmetric Encryption: For securing sensitive fields (e.g., GPS coordinates, device IDs).
3. RSA Digital Signatures: For municipal server authenticity and non-repudiation.
"""

import json
import base64
import hashlib
import hmac
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

import config


def _ensure_keys_exist():
    """Ensure key files exist; generate them if missing."""
    fernet_path = Path(config.FERNET_KEY_FILE)
    priv_path = Path(config.RSA_PRIVATE_KEY_FILE)
    pub_path = Path(config.RSA_PUBLIC_KEY_FILE)

    if not fernet_path.exists() or not priv_path.exists() or not pub_path.exists():
        from scripts.generate_keys import generate_fernet_key, generate_rsa_keypair
        generate_fernet_key()
        generate_rsa_keypair()


# ----------------------------------------------------------------------
# 1. Fernet Symmetric Encryption
# ----------------------------------------------------------------------

def get_fernet_cipher() -> Fernet:
    """Load Fernet key from disk and return a Fernet cipher instance."""
    _ensure_keys_exist()
    with open(config.FERNET_KEY_FILE, "rb") as f:
        key = f.read().strip()
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """
    Encrypt a plaintext string using Fernet (AES-128 in CBC mode + HMAC-SHA256).
    Returns a URL-safe base64-encoded ciphertext string.
    """
    if value is None:
        return ""
    cipher = get_fernet_cipher()
    ciphertext_bytes = cipher.encrypt(str(value).encode("utf-8"))
    return ciphertext_bytes.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt a Fernet ciphertext string back to plaintext.
    Handles errors gracefully if key is incorrect or data is corrupted.
    """
    if not ciphertext:
        return ""
    try:
        cipher = get_fernet_cipher()
        plaintext_bytes = cipher.decrypt(ciphertext.encode("utf-8"))
        return plaintext_bytes.decode("utf-8")
    except Exception as e:
        return f"[DECRYPTION_ERROR: {str(e)}]"


# ----------------------------------------------------------------------
# 2. Canonical Representation & SHA-256 Hashing
# ----------------------------------------------------------------------

CANONICAL_FIELDS = [
    "device_id",
    "timestamp",
    "latitude",
    "longitude",
    "event_type",
    "confidence",
    "pdi_score"
]


def build_canonical_string(data: dict) -> str:
    """
    Build a deterministic, canonical JSON string from specified core record fields.
    Rounds floats to 6 decimal places to prevent floating-point discrepancies across platforms.
    """
    canonical_dict = {}
    for key in sorted(CANONICAL_FIELDS):
        val = data.get(key)
        if isinstance(val, float):
            canonical_dict[key] = round(val, 6)
        elif val is None:
            canonical_dict[key] = ""
        else:
            canonical_dict[key] = str(val)

    return json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))


def compute_sha256(canonical_str: str) -> str:
    """Compute the SHA-256 hexadecimal digest of a canonical string."""
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def verify_sha256(canonical_str: str, expected_hash: str) -> bool:
    """
    Verify whether the canonical string produces the expected SHA-256 digest.
    Uses hmac.compare_digest to prevent timing attacks.
    """
    current_hash = compute_sha256(canonical_str)
    return hmac.compare_digest(current_hash.lower(), expected_hash.lower())


# ----------------------------------------------------------------------
# 3. RSA Digital Signatures
# ----------------------------------------------------------------------

def get_rsa_private_key():
    """Load the RSA private key from PEM file."""
    _ensure_keys_exist()
    with open(config.RSA_PRIVATE_KEY_FILE, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def get_rsa_public_key():
    """Load the RSA public key from PEM file."""
    _ensure_keys_exist()
    with open(config.RSA_PUBLIC_KEY_FILE, "rb") as f:
        return serialization.load_pem_public_key(f.read())


def sign_data(canonical_str: str) -> str:
    """
    Sign canonical data using RSA private key and SHA-256 with PKCS#1 v1.5 padding.
    Returns base64-encoded signature string.
    """
    private_key = get_rsa_private_key()
    signature = private_key.sign(
        canonical_str.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")


def verify_signature(canonical_str: str, signature_b64: str) -> bool:
    """
    Verify an RSA digital signature against the canonical string using the public key.
    Returns True if signature is valid, False otherwise.
    """
    if not signature_b64:
        return False
    try:
        public_key = get_rsa_public_key()
        sig_bytes = base64.b64decode(signature_b64.encode("utf-8"))
        public_key.verify(
            sig_bytes,
            canonical_str.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except (InvalidSignature, ValueError, Exception):
        return False
