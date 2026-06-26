import pytest

from branta.v2.encryption import AesEncryption


class TestAesEncryption:
    async def test_encrypt_decrypt_roundtrip(self):
        value = "hello world"
        secret = "my-secret"
        encrypted = await AesEncryption.encrypt(value, secret)
        decrypted = await AesEncryption.decrypt(encrypted, secret)
        assert decrypted == value

    async def test_encrypt_produces_base64(self):
        import base64
        encrypted = await AesEncryption.encrypt("test", "secret")
        base64.b64decode(encrypted)  # should not raise

    async def test_decrypt_wrong_key_raises(self):
        encrypted = await AesEncryption.encrypt("test value", "correct-key")
        with pytest.raises(Exception, match="Decryption failed"):
            await AesEncryption.decrypt(encrypted, "wrong-key")

    async def test_decrypt_invalid_base64_raises(self):
        with pytest.raises(Exception, match="Decryption failed"):
            await AesEncryption.decrypt("not valid base64!!!", "key")

    async def test_decrypt_too_short_raises(self):
        import base64
        short = base64.b64encode(b"short").decode()
        with pytest.raises(Exception, match="too short"):
            await AesEncryption.decrypt(short, "key")

    async def test_deterministic_nonce_produces_same_ciphertext(self):
        value = "lnbc100n1ptest"
        secret = "abc123"
        enc1 = await AesEncryption.encrypt(value, secret, deterministic_nonce=True)
        enc2 = await AesEncryption.encrypt(value, secret, deterministic_nonce=True)
        assert enc1 == enc2

    async def test_random_nonce_produces_different_ciphertexts(self):
        value = "test-value"
        secret = "test-secret"
        enc1 = await AesEncryption.encrypt(value, secret, deterministic_nonce=False)
        enc2 = await AesEncryption.encrypt(value, secret, deterministic_nonce=False)
        assert enc1 != enc2

    async def test_deterministic_nonce_decrypts_correctly(self):
        value = "ark1testaddress"
        secret = "hash-key"
        encrypted = await AesEncryption.encrypt(value, secret, deterministic_nonce=True)
        decrypted = await AesEncryption.decrypt(encrypted, secret)
        assert decrypted == value

    async def test_unicode_values_roundtrip(self):
        value = "test-value-with-unicode-é"
        secret = "unicode-secret-à"
        encrypted = await AesEncryption.encrypt(value, secret)
        decrypted = await AesEncryption.decrypt(encrypted, secret)
        assert decrypted == value
