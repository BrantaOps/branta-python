from __future__ import annotations

import re
import uuid
from dataclasses import replace
from typing import Dict, List, Optional, Set
from urllib.parse import quote

from branta.enums import DestinationType, VerifyStatus, is_secret_key_address_type
from branta.exceptions import BrantaPaymentException, IncompleteError
from branta.extensions import get_base_url, get_derived_key_type, to_normalized_hash, to_url_fragment
from branta.models import AddPaymentResult, Destination, Payment, Platform, VerifyResult
from branta.options import BrantaApiOptions
from branta.builder import PaymentBuilder
from branta.client import BrantaClient
from branta.encryption import AesEncryptionService
from branta.parser import QRParser, detect_destination_type
from branta.secret_generator import GuidSecretGenerator
from branta.serialization import fold_description_into_metadata, lift_description_from_metadata

class TamperedError(Exception):
    pass


def _matched_destinations_from(payments: List[Payment]) -> List[Destination]:
    matched: List[Destination] = []
    for payment in payments:
        for destination in payment.destinations:
            if destination.is_encrypted is False:
                matched.append(replace(destination))
    return matched


def _to_verify_result(payments: List[Payment], verify_url: str) -> VerifyResult:
    if not payments:
        return VerifyResult(status=VerifyStatus.Unknown, verify_url=verify_url)
    return VerifyResult(
        status=VerifyStatus.Match,
        verify_url=verify_url,
        payments=payments,
        matched_destinations=_matched_destinations_from(payments),
    )


def _copy_platform(platform: Optional[Platform]) -> Optional[Platform]:
    if platform is None:
        return None
    return replace(platform)


def _copy_payment(payment: Payment) -> Payment:
    return replace(
        payment,
        destinations=[replace(destination) for destination in payment.destinations],
        parent_platform=_copy_platform(payment.parent_platform),
        child_platform=_copy_platform(payment.child_platform),
    )


def _is_bech32(value: str) -> bool:
    return re.match(r"^(bc|tb|bcrt)1", value, re.IGNORECASE) is not None


def _addresses_match(left: str, right: str) -> bool:
    if _is_bech32(left) and _is_bech32(right):
        return left.lower() == right.lower()
    if left.lower().startswith("0x") and right.lower().startswith("0x"):
        return left.lower() == right.lower()
    return left == right


def _uniform_secret_key_address(parser: QRParser) -> Optional[str]:
    """Shared secret-key address across the QR, or None. Conflicting values are tampered."""
    addresses = [
        destination.value
        for destination in parser.destinations
        if destination.secret_key and destination.value.strip() != ""
    ]
    if not addresses:
        return None
    first = addresses[0]
    for address in addresses[1:]:
        if not _addresses_match(first, address):
            raise TamperedError()
    return first


def _encode_uri_component(value: str) -> str:
    return quote(value, safe="-_.!~*'()")


class BrantaService:
    def __init__(
        self,
        options: BrantaApiOptions,
        *,
        client: Optional[BrantaClient] = None,
        aes_encryption: Optional[AesEncryptionService] = None,
        secret_generator: Optional[GuidSecretGenerator] = None,
    ) -> None:
        self._default_options = options
        self._client = client if client is not None else BrantaClient(options)
        self._aes_encryption = aes_encryption if aes_encryption is not None else AesEncryptionService()
        self._secret_generator = secret_generator if secret_generator is not None else GuidSecretGenerator()

    def create_payment_builder(self) -> PaymentBuilder:
        return PaymentBuilder()

    async def verify(self, input: str, options: Optional[BrantaApiOptions] = None) -> VerifyResult:
        parser = QRParser(input)
        if parser.on_chain_encryption_text is not None:
            lookup = parser.on_chain_encryption_text
        elif parser.destination is not None:
            lookup = parser.destination
        else:
            lookup = ""

        try:
            expected_secret_key_address = _uniform_secret_key_address(parser)

            if parser.has_unverifiable_instruction:
                return VerifyResult(status=VerifyStatus.Unknown, verify_url=self._build_verify_url(options, lookup))

            if parser.has_branta_params():
                additional_values = [
                    destination.value
                    for destination in parser.destinations
                    if get_derived_key_type(destination.value) is not None
                ]
                if expected_secret_key_address is None and not additional_values:
                    return VerifyResult(status=VerifyStatus.Unknown, verify_url=self._build_verify_url(options, lookup))
                payments, verify_url = await self._lookup_by_branta_id(
                    parser.on_chain_encryption_text or "",
                    parser.on_chain_encryption_secret,
                    additional_values,
                    expected_secret_key_address,
                    set(parser.expected_secret_key_types),
                    options,
                )
                return _to_verify_result(payments, verify_url)

            destination = parser.destination or ""
            if get_derived_key_type(destination) is None:
                return VerifyResult(status=VerifyStatus.Unknown, verify_url=self._build_verify_url(options, destination))

            payments, verify_url = await self._lookup_by_derived_key(destination, options)
            return _to_verify_result(payments, verify_url)
        except TamperedError:
            return VerifyResult(status=VerifyStatus.Tampered, verify_url=self._build_verify_url(options, lookup))
        except IncompleteError:
            return VerifyResult(status=VerifyStatus.Incomplete, verify_url=self._build_verify_url(options, lookup))

    async def _lookup_by_branta_id(
        self,
        lookup_value: str,
        encryption_key: Optional[str],
        additional_hash_values: List[str],
        expected_secret_key_address: Optional[str],
        expected_secret_key_types: Set[DestinationType],
        options: Optional[BrantaApiOptions],
    ) -> tuple[List[Payment], str]:
        payments = await self._client.get_payments(lookup_value, options)
        keys: Dict[str, str] = {}
        bound: List[Payment] = []
        for payment in payments:
            secret_key_bound = await self._decrypt_destinations(
                payment,
                encryption_key,
                keys,
                expected_secret_key_address,
                expected_secret_key_types,
            )
            hashes_bound = True
            for value in additional_hash_values:
                if not await self._decrypt_derived_key_destinations(payment, value, keys):
                    hashes_bound = False
            has_payable_instruction = (
                expected_secret_key_address is not None or len(additional_hash_values) > 0
            )
            if has_payable_instruction and secret_key_bound and hashes_bound:
                bound.append(payment)
        return bound, self._build_verify_url(options, lookup_value, keys)

    async def _decrypt_derived_key_destinations(
        self,
        payment: Payment,
        plain_value: str,
        keys: Dict[str, str],
    ) -> bool:
        derived_type = get_derived_key_type(plain_value)
        if derived_type is None:
            return False

        key = to_normalized_hash(plain_value)
        bound = False
        for destination in payment.destinations:
            if destination.is_encrypted is False or destination.type != derived_type:
                continue
            try:
                decrypted = await self._aes_encryption.decrypt(destination.value, key)
            except Exception:
                continue
            if decrypted.lower() != plain_value.lower():
                raise TamperedError()
            destination.value = decrypted
            destination.is_encrypted = False
            if destination.id is not None and destination.id not in keys:
                keys[destination.id] = key
            await self._try_decrypt_metadata(payment, destination, key)
            bound = True
        return bound

    async def _lookup_by_derived_key(
        self,
        destination_value: str,
        options: Optional[BrantaApiOptions],
    ) -> tuple[List[Payment], str]:
        normalized_destination = destination_value.lower()
        lookup_value = await self._aes_encryption.encrypt(
            normalized_destination,
            to_normalized_hash(normalized_destination),
            True,
        )
        payments = await self._client.get_payments(lookup_value, options)
        keys: Dict[str, str] = {}
        bound: List[Payment] = []
        for payment in payments:
            if await self._decrypt_derived_key_destinations(payment, normalized_destination, keys):
                bound.append(payment)
        return bound, self._build_verify_url(options, lookup_value, keys)

    async def _decrypt_destinations(
        self,
        payment: Payment,
        encryption_key: Optional[str],
        keys: Dict[str, str],
        expected_secret_key_address: Optional[str],
        expected_secret_key_types: Set[DestinationType],
    ) -> bool:
        # No secret-key instruction on the QR → leave every secret-key rail encrypted.
        secret_key_bound = expected_secret_key_address is None
        decrypted_expected_rail = False
        for destination in payment.destinations:
            if destination.is_encrypted is False:
                continue
            if destination.type is None or not is_secret_key_address_type(destination.type):
                continue
            # Only this QR's rail family (e.g. polygon when scanning pol:). Empty = none.
            if destination.type not in expected_secret_key_types:
                continue
            if encryption_key is None:
                continue
            try:
                decrypted = await self._aes_encryption.decrypt(destination.value, encryption_key)
            except Exception:
                continue
            decrypted_expected_rail = True
            # Match-if-any within the family: a sibling rail with a different address stays encrypted.
            if expected_secret_key_address is not None and not _addresses_match(
                decrypted, expected_secret_key_address
            ):
                continue
            if expected_secret_key_address is not None:
                secret_key_bound = True
            destination.value = decrypted
            destination.is_encrypted = False
            if destination.id is not None and destination.id not in keys:
                keys[destination.id] = encryption_key
            await self._try_decrypt_metadata(payment, destination, encryption_key)
        # Tampered only when a family rail decrypted and none matched the scanned address.
        if expected_secret_key_address is not None and not secret_key_bound and decrypted_expected_rail:
            raise TamperedError()
        return secret_key_bound

    async def _try_decrypt_metadata(self, payment: Payment, destination: Destination, key_used: str) -> None:
        if destination.encrypted_dek is None or payment.metadata is None or payment.is_metadata_decrypted:
            return
        try:
            dek = await self._aes_encryption.decrypt(destination.encrypted_dek, key_used)
            payment.metadata = await self._aes_encryption.decrypt(payment.metadata, dek)
            payment.is_metadata_decrypted = True
            lift_description_from_metadata(payment)
        except Exception:
            return

    async def add_payment(self, payment: Payment, options: Optional[BrantaApiOptions] = None) -> AddPaymentResult:
        submitted = _copy_payment(payment)
        fold_description_into_metadata(submitted)
        dek: Optional[str] = None
        if submitted.metadata is not None and submitted.destinations:
            dek = self._secret_generator.generate()
            submitted.metadata = await self._aes_encryption.encrypt(submitted.metadata, dek, False)

        secret = self._secret_generator.generate()
        encrypted_to_key: Dict[str, str] = {}

        for destination in submitted.destinations:
            if destination.id is None:
                destination.id = str(uuid.uuid4())

            detected = destination.type if destination.type is not None else detect_destination_type(destination.value)
            if destination.type is None and detected is not None:
                destination.type = detected

            if detected is not None and is_secret_key_address_type(detected):
                destination.value = await self._aes_encryption.encrypt(
                    destination.value,
                    secret,
                    self._secret_generator.deterministic_nonce,
                )
                encrypted_to_key[destination.value] = secret
                if dek is not None:
                    destination.encrypted_dek = await self._aes_encryption.encrypt(dek, secret, False)
            else:
                derived_type = get_derived_key_type(destination.value)
                if derived_type is None:
                    label = destination.type.value if isinstance(destination.type, DestinationType) else destination.type
                    raise BrantaPaymentException(f"destination type '{label}' cannot be encrypted")
                normalized_value = destination.value.lower()
                key = to_normalized_hash(normalized_value)
                destination.value = await self._aes_encryption.encrypt(normalized_value, key, True)
                encrypted_to_key[destination.value] = key
                if dek is not None:
                    destination.encrypted_dek = await self._aes_encryption.encrypt(dek, key, False)

        response_payment = await self._client.post_payment(submitted, options)
        if response_payment is None:
            raise BrantaPaymentException("No payment returned from server.")

        keys: Dict[str, str] = {}
        for destination in response_payment.destinations:
            if destination.id is not None and destination.value in encrypted_to_key:
                keys[destination.id] = encrypted_to_key[destination.value]

        primary_value = submitted.destinations[0].value if submitted.destinations else ""
        verify_url = self._build_verify_url(options, primary_value, keys)
        return AddPaymentResult(payment=response_payment, secret=secret, verify_url=verify_url)

    async def is_api_key_valid(self, options: Optional[BrantaApiOptions] = None) -> bool:
        return await self._client.is_api_key_valid(options)

    def _build_verify_url(
        self,
        options: Optional[BrantaApiOptions],
        payment_lookup: str,
        keys: Optional[Dict[str, str]] = None,
    ) -> str:
        base_url = get_base_url(self._default_options, options)
        url = f"{base_url}/v2/verify/{_encode_uri_component(payment_lookup)}"
        if keys:
            url += to_url_fragment(keys)
        return url
