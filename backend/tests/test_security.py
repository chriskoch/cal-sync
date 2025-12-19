"""
Unit tests for security functions (password hashing, JWT, encryption).
"""
import pytest
from datetime import timedelta
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    encrypt_token,
    decrypt_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing works."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test that correct password verification works."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test that incorrect password verification fails."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test JWT token with custom expiration."""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)

        assert isinstance(token, str)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test@example.com"

    def test_decode_access_token_valid(self):
        """Test decoding a valid JWT token."""
        data = {"sub": "test@example.com", "custom": "value"}
        token = create_access_token(data)

        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test@example.com"
        assert decoded["custom"] == "value"
        assert "exp" in decoded

    def test_decode_access_token_invalid(self):
        """Test decoding an invalid JWT token."""
        invalid_token = "invalid.token.here"

        decoded = decode_access_token(invalid_token)
        assert decoded is None

    def test_decode_access_token_malformed(self):
        """Test decoding a malformed JWT token."""
        malformed_token = "not-a-jwt-token"

        decoded = decode_access_token(malformed_token)
        assert decoded is None


@pytest.mark.unit
class TestEncryption:
    """Test OAuth token encryption and decryption."""

    def test_encrypt_token(self):
        """Test token encryption."""
        original_token = "test_oauth_token_12345"
        encrypted = encrypt_token(original_token)

        assert encrypted != original_token
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_decrypt_token(self):
        """Test token decryption."""
        original_token = "test_oauth_token_12345"
        encrypted = encrypt_token(original_token)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original_token

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        tokens = [
            "simple_token",
            "complex_token_with_special_chars!@#$%",
            "long_token_" * 100,
            "",  # Edge case: empty string
        ]

        for token in tokens:
            encrypted = encrypt_token(token)
            decrypted = decrypt_token(encrypted)
            assert decrypted == token, f"Failed for token: {token}"

    def test_fernet_encryption_format(self):
        """Test that Fernet encryption produces valid format."""
        token = "test_token"
        encrypted = encrypt_token(token)

        # Fernet tokens are base64-encoded and start with a version byte
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        # Fernet encrypted strings are typically much longer than the original
        assert len(encrypted) > len(token)
