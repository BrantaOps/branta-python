from __future__ import annotations

from typing import Dict, List, Optional
from urllib.parse import quote

from branta.enums import DestinationType, PrivacyMode
from branta.exceptions import BrantaPaymentException
from branta.extensions import (
    get_base_url,
    get_hash_zk_type,
    get_privacy,
    to_normalized_hash,
    to_url_fragment,
)
from branta.models import AddPaymentResult, Destination, Payment, PaymentsResult
from branta.options import BrantaClientOptions
from branta.v2.builder import PaymentBuilder
from branta.v2.client import BrantaClient
from branta.v2.encryption import AesEncryptionService
from branta.v2.parser import QRParser
from branta.v2.secret_generator import GuidSecretGenerator


class BrantaService:
    def __init__(
        self,
        default_options: Optional[BrantaClientOptions] = None,
        *,
        client: Optional[object] = None,
        aes_encryption: Optional[object] = None,
        secret_generator: Optional[object] = None,
    ) -> None:
        self._default_options = default_options
        self._client = client if client is not None else BrantaClient(default_options)
        self._aes_encryption = aes_encryption if aes_encryption is not None else AesEncryptionService()
        self._secret_generator = secret_generator if secret_generator is not None else GuidSecretGenerator()

    def create_payment_builder(self) -> PaymentBuilder:
        return PaymentBuilder()

    async def get_payments_by_qr_code(
        self,
        qr_text: str,
        options: Optional[BrantaClientOptions] = None,
    ) -> PaymentsResult:
        parser = QRParser(qr_text)

        if parser.is_on_chain_zk():
            additional_values = [
                d.value
                for d in parser.destinations
                if get_hash_zk_type(d.value) is not None
            ]
            return await self._get_payments_for_zk(
                parser.on_chain_encryption_text,
                parser.on_chain_encryption_secret,
                additional_values,
                options,
            )

        destination = parser.destination
        if destination is None:
            return PaymentsResult(payments=[], verify_url=self._build_verify_url(options, ""))

        if (
            get_privacy(self._default_options, options) == PrivacyMode.Strict
            and get_hash_zk_type(destination) is None
        ):
            return PaymentsResult(payments=[], verify_url=self._build_verify_url(options, destination))

        return await self.get_payments(destination, None, options)

    async def get_payments(
        self,
        destination_value: str,
        destination_encryption_key: Optional[str] = None,
        options: Optional[BrantaClientOptions] = None,
    ) -> PaymentsResult:
        hash_zk_type = get_hash_zk_type(destination_value)

        if (
            hash_zk_type is None
            and destination_encryption_key is None
            and get_privacy(self._default_options, options) == PrivacyMode.Strict
        ):
            raise BrantaPaymentException(
                "PrivacyMode.Strict does not permit plain-text lookups for this destination type."
            )

        normalized_destination = destination_value.lower() if hash_zk_type is not None else destination_value
        lookup_value = normalized_destination

        if hash_zk_type is not None:
            lookup_value = await self._aes_encryption.encrypt(
                normalized_destination,
                to_normalized_hash(normalized_destination),
                True,
            )

        payments = await self._client.get_payments(lookup_value, options)

        if (
            len(payments) == 0
            and hash_zk_type is not None
            and get_privacy(self._default_options, options) != PrivacyMode.Strict
        ):
            lookup_value = normalized_destination
            payments = await self._client.get_payments(lookup_value, options)

        keys: Dict[str, str] = {}
        for payment in payments:
            await self._decrypt_destinations(payment, normalized_destination, destination_encryption_key, hash_zk_type, keys)

        return PaymentsResult(payments=payments, verify_url=self._build_verify_url(options, lookup_value, keys))

    async def add_payment(
        self,
        payment: Payment,
        options: Optional[BrantaClientOptions] = None,
    ) -> AddPaymentResult:
        if (
            get_privacy(self._default_options, options) == PrivacyMode.Strict
            and any(not d.is_zk for d in payment.destinations)
        ):
            raise BrantaPaymentException(
                "PrivacyMode.Strict requires all destinations to be ZK; one or more destinations have is_zk = False."
            )

        dek: Optional[str] = None
        if payment.metadata is not None and any(d.is_zk for d in payment.destinations):
            dek = self._secret_generator.generate()
            payment.metadata = await self._aes_encryption.encrypt(payment.metadata, dek, False)

        secret = self._secret_generator.generate()
        encrypted_to_key: Dict[str, str] = {}

        for destination in payment.destinations:
            if not destination.is_zk:
                continue

            if destination.type == DestinationType.BitcoinAddress:
                destination.value = await self._aes_encryption.encrypt(
                    destination.value, secret, self._secret_generator.deterministic_nonce
                )
                encrypted_to_key[destination.value] = secret
                if dek is not None:
                    destination.encrypted_dek = await self._aes_encryption.encrypt(dek, secret, False)
            else:
                hash_zk_type = get_hash_zk_type(destination.value)
                if hash_zk_type is None:
                    raise BrantaPaymentException(
                        f"destination type '{destination.type}' does not support ZK"
                    )
                normalized_value = destination.value.lower()
                key = to_normalized_hash(normalized_value)
                destination.value = await self._aes_encryption.encrypt(normalized_value, key, True)
                encrypted_to_key[destination.value] = key
                if dek is not None:
                    destination.encrypted_dek = await self._aes_encryption.encrypt(dek, key, False)

        response_payment = await self._client.post_payment(payment, options)
        if response_payment is None:
            raise BrantaPaymentException("No payment returned from server.")

        keys: Dict[str, str] = {}
        for d in response_payment.destinations:
            if d.zk_id is not None and d.value in encrypted_to_key:
                keys[d.zk_id] = encrypted_to_key[d.value]

        primary_value = payment.destinations[0].value if payment.destinations else ""
        verify_url = self._build_verify_url(options, primary_value, keys)

        return AddPaymentResult(payment=response_payment, secret=secret, verify_url=verify_url)

    async def is_api_key_valid(self, options: Optional[BrantaClientOptions] = None) -> bool:
        return await self._client.is_api_key_valid(options)

    async def close(self) -> None:
        if hasattr(self._client, "close"):
            await self._client.close()

    async def __aenter__(self) -> "BrantaService":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # ---- private helpers ----

    async def _get_payments_for_zk(
        self,
        lookup_value: str,
        encryption_key: Optional[str],
        additional_hash_values: List[str],
        options: Optional[BrantaClientOptions],
    ) -> PaymentsResult:
        payments = await self._client.get_payments(lookup_value, options)

        keys: Dict[str, str] = {}
        for payment in payments:
            await self._decrypt_destinations(payment, lookup_value, encryption_key, None, keys)
            for value in additional_hash_values:
                await self._decrypt_hash_zk_destinations(payment, value, keys)

        return PaymentsResult(payments=payments, verify_url=self._build_verify_url(options, lookup_value, keys))

    async def _decrypt_hash_zk_destinations(
        self,
        payment: Payment,
        plain_value: str,
        keys: Dict[str, str],
    ) -> None:
        hash_zk_type = get_hash_zk_type(plain_value)
        if hash_zk_type is None:
            return
        key = to_normalized_hash(plain_value)
        for destination in payment.destinations:
            if not destination.is_zk or destination.type != hash_zk_type:
                continue
            try:
                destination.value = await self._aes_encryption.decrypt(destination.value, key)
                destination.is_encrypted = False
                if destination.zk_id is not None and destination.zk_id not in keys:
                    keys[destination.zk_id] = key
                await self._try_decrypt_metadata(payment, destination, key)
            except Exception:
                pass

    async def _decrypt_destinations(
        self,
        payment: Payment,
        destination_value: str,
        encryption_key: Optional[str],
        hash_zk_type: Optional[DestinationType],
        keys: Dict[str, str],
    ) -> None:
        for destination in payment.destinations:
            destination.is_encrypted = bool(destination.is_zk)
            if not destination.is_zk:
                continue

            if destination.type == DestinationType.BitcoinAddress:
                if encryption_key is None:
                    continue
                try:
                    destination.value = await self._aes_encryption.decrypt(destination.value, encryption_key)
                    destination.is_encrypted = False
                    if destination.zk_id is not None and destination.zk_id not in keys:
                        keys[destination.zk_id] = encryption_key
                    await self._try_decrypt_metadata(payment, destination, encryption_key)
                except Exception:
                    pass
            elif hash_zk_type is not None and destination.type == hash_zk_type:
                key = to_normalized_hash(destination_value)
                try:
                    destination.value = await self._aes_encryption.decrypt(destination.value, key)
                    destination.is_encrypted = False
                    if destination.zk_id is not None and destination.zk_id not in keys:
                        keys[destination.zk_id] = key
                    await self._try_decrypt_metadata(payment, destination, key)
                except Exception:
                    pass

    async def _try_decrypt_metadata(
        self,
        payment: Payment,
        destination: Destination,
        key_used: str,
    ) -> None:
        if destination.encrypted_dek is None or payment.metadata is None or payment.is_metadata_decrypted:
            return
        try:
            dek = await self._aes_encryption.decrypt(destination.encrypted_dek, key_used)
            payment.metadata = await self._aes_encryption.decrypt(payment.metadata, dek)
            payment.is_metadata_decrypted = True
        except Exception:
            pass

    def _build_verify_url(
        self,
        options: Optional[BrantaClientOptions],
        payment_lookup: str,
        keys: Optional[Dict[str, str]] = None,
    ) -> str:
        base_url = get_base_url(self._default_options, options)
        encoded = quote(payment_lookup, safe="")
        url = f"{base_url}/v2/verify/{encoded}"
        if keys:
            url += to_url_fragment(keys)
        return url
