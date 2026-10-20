"""
Cryptographic service for encrypting and decrypting sensitive credentials.
Protects API keys, bearer tokens, basic auth passwords, and sensitive headers at rest.
"""

import base64
import hashlib
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

def _get_fernet_key() -> bytes:
    """
    Derives a valid 32-byte urlsafe base64-encoded key from settings.FIELD_ENCRYPTION_KEY
    or SECRET_KEY to ensure valid Fernet operation.
    """
    raw_key = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or getattr(settings, 'SECRET_KEY', 'default-key')
    try:
        # Check if already a valid 32-byte urlsafe base64 key
        decoded = base64.urlsafe_b64decode(raw_key.encode('utf-8'))
        if len(decoded) == 32:
            return raw_key.encode('utf-8')
    except Exception:
        pass

    # Deterministically derive 32 bytes from SHA-256 of the raw key
    digest = hashlib.sha256(raw_key.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_secret(plaintext: str) -> str:
    """
    Encrypts a plaintext secret string using AES-CBC with HMAC authentication (Fernet).
    Returns base64 ciphertext string.
    """
    if not plaintext:
        return ""
    key = _get_fernet_key()
    fernet = Fernet(key)
    return fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypts a ciphertext string back to plaintext.
    Returns empty string if decryption fails or input is empty.
    """
    if not ciphertext:
        return ""
    key = _get_fernet_key()
    fernet = Fernet(key)
    try:
        return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception):
        return "[Decryption Error: Invalid Key]"


def mask_secret(secret: str, visible_chars: int = 4) -> str:
    """
    Returns a masked version of a secret for safe UI display and logging.
    e.g. 'bearer_tok_123456789' -> 'bear••••789'
    """
    if not secret:
        return ""
    length = len(secret)
    if length <= visible_chars * 2:
        return "••••••••"
    prefix = secret[:visible_chars]
    suffix = secret[-visible_chars:]
    return f"{prefix}••••••••{suffix}"
