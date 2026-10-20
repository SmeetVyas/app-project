"""
Unit tests for Cryptographic credential encryption, decryption, and masking.
"""

from services.crypto_service import encrypt_secret, decrypt_secret, mask_secret


class TestCryptoService:
    def test_encrypt_and_decrypt_cycle(self):
        secret = "sk_live_948201840294829104"
        ciphertext = encrypt_secret(secret)
        assert ciphertext != secret
        assert len(ciphertext) > 20
        
        decrypted = decrypt_secret(ciphertext)
        assert decrypted == secret

    def test_empty_string_handling(self):
        assert encrypt_secret("") == ""
        assert decrypt_secret("") == ""
        assert mask_secret("") == ""

    def test_invalid_ciphertext_returns_error_safely(self):
        result = decrypt_secret("gibberish-not-valid-base64-or-fernet")
        assert "[Decryption Error" in result

    def test_secret_masking(self):
        masked = mask_secret("sk_test_123456789")
        assert masked.startswith("sk_t")
        assert masked.endswith("6789")
        assert "••••" in masked
        assert mask_secret("short") == "••••••••"
