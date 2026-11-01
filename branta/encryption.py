from __future__ import annotations

import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_LENGTH = 12


class AesEncryption:
    @staticmethod
    async def encrypt(value: str, secret: str, deterministic_nonce: bool = False) -> str:
        try:
            key = hashlib.sha256(secret.encode("utf-8")).digest()

            if deterministic_nonce:
                nonce = hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()[:_NONCE_LENGTH]
            else:
                nonce = os.urandom(_NONCE_LENGTH)

            aesgcm = AESGCM(key)
            ciphertext_and_tag = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
            result = nonce + ciphertext_and_tag
            return base64.b64encode(result).decode("utf-8")
        except Exception as e:
            raise Exception(f"Encryption failed: {e}") from e

    @staticmethod
    async def decrypt(encrypted_value: str, secret: str) -> str:
        try:
            encrypted_data = base64.b64decode(encrypted_value)
        except Exception as e:
            raise Exception(f"Decryption failed: {e}") from e

        if len(encrypted_data) < 28:
            raise Exception("Invalid encrypted data: too short")

        try:
            key = hashlib.sha256(secret.encode("utf-8")).digest()
            nonce = encrypted_data[:_NONCE_LENGTH]
            ciphertext_and_tag = encrypted_data[_NONCE_LENGTH:]

            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            raise Exception(f"Decryption failed: {e}") from e


class AesEncryptionService:
    async def encrypt(self, value: str, secret: str, deterministic_nonce: bool = False) -> str:
        return await AesEncryption.encrypt(value, secret, deterministic_nonce)

    async def decrypt(self, encrypted_value: str, secret: str) -> str:
        return await AesEncryption.decrypt(encrypted_value, secret)
