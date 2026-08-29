from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from branta.enums import BrantaServerBaseUrl, DestinationType, PrivacyMode
from branta.exceptions import BrantaPaymentException, BrantaPaymentExceptionReason
from branta.extensions import to_normalized_hash
from branta.models import Payment
from branta.options import BrantaClientOptions
from branta.v2.builder import PaymentBuilder
from branta.v2.service import BrantaService

BITCOIN_ADDRESS = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
ENCRYPTED_BITCOIN_ADDRESS = "encrypted-bitcoin-address"
SECRET = "test-secret"

BOLT11_INVOICE = "lnbc100n1ptest"
ENCRYPTED_BOLT11 = "encrypted-bolt11-value"
DECRYPTED_BOLT11 = "lnbc100n1pdecrypted"

ARK_ADDRESS = "ark100testaddress"
ENCRYPTED_ARK_ADDRESS = "encrypted-ark-address"


def make_client_mock():
    mock = MagicMock()
    mock.get_payments = AsyncMock(return_value=[])
    mock.post_payment = AsyncMock(return_value=None)
    mock.is_api_key_valid = AsyncMock(return_value=False)
    return mock


def make_aes_mock(bolt11_hash: str, ark_hash: str):
    mock = MagicMock()

    async def encrypt_side_effect(value, secret, deterministic_nonce=False):
        if value == BOLT11_INVOICE and secret == bolt11_hash:
            return ENCRYPTED_BOLT11
        if value == BITCOIN_ADDRESS and secret == SECRET:
            return ENCRYPTED_BITCOIN_ADDRESS
        if value == ARK_ADDRESS and secret == ark_hash:
            return ENCRYPTED_ARK_ADDRESS
        return ""

    async def decrypt_side_effect(encrypted_value, secret):
        if encrypted_value == ENCRYPTED_BITCOIN_ADDRESS and secret == SECRET:
            return BITCOIN_ADDRESS
        if encrypted_value == ENCRYPTED_BOLT11 and secret == bolt11_hash:
            return DECRYPTED_BOLT11
        return ""

    mock.encrypt = AsyncMock(side_effect=encrypt_side_effect)
    mock.decrypt = AsyncMock(side_effect=decrypt_side_effect)
    return mock


def make_secret_mock():
    mock = MagicMock()
    mock.generate = MagicMock(return_value=SECRET)
    mock.deterministic_nonce = False
    return mock


def plain_bitcoin_payment() -> Payment:
    return PaymentBuilder().add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()


def zk_bitcoin_payment() -> Payment:
    return PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).set_zk().build()


def zk_bolt11_payment() -> Payment:
    return PaymentBuilder().add_destination(ENCRYPTED_BOLT11, DestinationType.Bolt11).set_zk().build()


def plain_bolt11_payment() -> Payment:
    return PaymentBuilder().add_destination(BOLT11_INVOICE, DestinationType.Bolt11).build()


def zk_ark_payment() -> Payment:
    return PaymentBuilder().add_destination(ENCRYPTED_ARK_ADDRESS, DestinationType.ArkAddress).set_zk().build()


BOLT11_HASH = to_normalized_hash(BOLT11_INVOICE)
ARK_HASH = to_normalized_hash(ARK_ADDRESS)

LOOSE_OPTIONS = BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Localhost,
    default_api_key="test-api-key",
    privacy=PrivacyMode.Loose,
)
STRICT_OPTIONS = BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Localhost,
    default_api_key="test-api-key",
    privacy=PrivacyMode.Strict,
)


@pytest.fixture
def client_mock():
    return make_client_mock()


@pytest.fixture
def aes_mock():
    return make_aes_mock(BOLT11_HASH, ARK_HASH)


@pytest.fixture
def secret_mock():
    return make_secret_mock()


@pytest.fixture
def service(client_mock, aes_mock, secret_mock):
    return BrantaService(
        LOOSE_OPTIONS,
        client=client_mock,
        aes_encryption=aes_mock,
        secret_generator=secret_mock,
    )


@pytest.fixture
def strict_service(client_mock, aes_mock, secret_mock):
    return BrantaService(
        STRICT_OPTIONS,
        client=client_mock,
        aes_encryption=aes_mock,
        secret_generator=secret_mock,
    )


# ===== get_payments_by_qr_code =====

class TestGetPaymentsByQrCode:
    async def test_zk_bitcoin_uri_uses_zk_params(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{BITCOIN_ADDRESS}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
        result = await service.get_payments_by_qr_code(qr)

        client_mock.get_payments.assert_awaited_with(ENCRYPTED_BITCOIN_ADDRESS, None)
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS

    async def test_plain_bitcoin_uri_uses_address(self, service, client_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == BITCOIN_ADDRESS:
                return [plain_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments_by_qr_code(f"bitcoin:{BITCOIN_ADDRESS}")

        client_mock.get_payments.assert_awaited_with(BITCOIN_ADDRESS, None)
        assert len(result.payments) == 1

    async def test_lightning_bolt11_uri_uses_encrypted_invoice_lookup(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [plain_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        await service.get_payments_by_qr_code(f"lightning:{BOLT11_INVOICE}")

        client_mock.get_payments.assert_awaited_with(ENCRYPTED_BOLT11, None)

    async def test_lightning_bolt11_uri_uppercase_uses_encrypted_lookup(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [plain_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        await service.get_payments_by_qr_code(f"lightning:{BOLT11_INVOICE.upper()}")

        client_mock.get_payments.assert_awaited_with(ENCRYPTED_BOLT11, None)

    async def test_lightning_bolt11_uri_leaves_unrelated_zk_bitcoin_encrypted(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(ENCRYPTED_BOLT11, DestinationType.Bolt11).set_zk()
            .add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).set_zk()
            .build()
        )

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [payment]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments_by_qr_code(f"lightning:{BOLT11_INVOICE}")

        assert len(result.payments) == 1
        assert result.payments[0].destinations[0].value == DECRYPTED_BOLT11
        assert result.payments[0].destinations[0].is_encrypted is False
        assert result.payments[0].destinations[1].value == ENCRYPTED_BITCOIN_ADDRESS
        assert result.payments[0].destinations[1].is_encrypted is True

    async def test_combined_zk_qr_decrypts_both_address_and_invoice(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).set_zk()
            .add_destination(ENCRYPTED_BOLT11, DestinationType.Bolt11).set_zk()
            .add_destination(ENCRYPTED_ARK_ADDRESS, DestinationType.ArkAddress).set_zk()
            .build()
        )

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [payment]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{BITCOIN_ADDRESS}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}&lightning={BOLT11_INVOICE}&ark={ARK_ADDRESS}"
        result = await service.get_payments_by_qr_code(qr)

        zk_id = payment.destinations[0].zk_id
        bolt11_zk_id = payment.destinations[1].zk_id
        ark_zk_id = payment.destinations[2].zk_id
        assert len(result.payments) == 1
        assert result.verify_url == (
            f"http://localhost:3000/v2/verify/{ENCRYPTED_BITCOIN_ADDRESS}"
            f"#k-{zk_id}={SECRET}&k-{bolt11_zk_id}={BOLT11_HASH}&k-{ark_zk_id}={ARK_HASH}"
        )
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS
        assert result.payments[0].destinations[1].value == DECRYPTED_BOLT11
        aes_mock.decrypt.assert_any_await(ENCRYPTED_BITCOIN_ADDRESS, SECRET)
        aes_mock.decrypt.assert_any_await(ENCRYPTED_BOLT11, BOLT11_HASH)


SWAPPED_ADDRESS = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
BECH32_ADDRESS = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
ENCRYPTED_BECH32_ADDRESS = "encrypted-bech32-address"


def zk_bech32_payment() -> Payment:
    return PaymentBuilder().add_destination(ENCRYPTED_BECH32_ADDRESS, DestinationType.BitcoinAddress).set_zk().build()


# ===== get_payments_by_qr_code address binding =====

class TestGetPaymentsByQrCodeAddressBinding:
    async def test_swapped_address_rejects(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{SWAPPED_ADDRESS}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
        with pytest.raises(BrantaPaymentException) as exc_info:
            await service.get_payments_by_qr_code(qr)
        assert exc_info.value.reason == BrantaPaymentExceptionReason.Tampered

    async def test_matching_address_does_not_throw(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{BITCOIN_ADDRESS}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
        result = await service.get_payments_by_qr_code(qr)
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS

    async def test_uppercase_bech32_qr_matches_lowercase_registered(self, service, client_mock, aes_mock):
        async def decrypt_side_effect(encrypted_value, secret):
            if encrypted_value == ENCRYPTED_BECH32_ADDRESS and secret == SECRET:
                return BECH32_ADDRESS
            return ""
        aes_mock.decrypt = AsyncMock(side_effect=decrypt_side_effect)

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BECH32_ADDRESS:
                return [zk_bech32_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{BECH32_ADDRESS.upper()}?branta_id={ENCRYPTED_BECH32_ADDRESS}&branta_secret={SECRET}"
        result = await service.get_payments_by_qr_code(qr)
        assert result.payments[0].destinations[0].value == BECH32_ADDRESS

    async def test_base58_case_mismatch_rejects(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{BITCOIN_ADDRESS.lower()}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
        with pytest.raises(BrantaPaymentException) as exc_info:
            await service.get_payments_by_qr_code(qr)
        assert exc_info.value.reason == BrantaPaymentExceptionReason.Tampered

    async def test_lightning_qr_with_zk_params_no_plain_address_decrypts_without_comparison(
        self, service, client_mock, aes_mock
    ):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"lightning:{BOLT11_INVOICE}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
        result = await service.get_payments_by_qr_code(qr)
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS

    async def test_combined_zk_qr_swapped_address_rejects(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).set_zk()
            .add_destination(ENCRYPTED_BOLT11, DestinationType.Bolt11).set_zk()
            .add_destination(ENCRYPTED_ARK_ADDRESS, DestinationType.ArkAddress).set_zk()
            .build()
        )

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [payment]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = (
            f"bitcoin:{SWAPPED_ADDRESS}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
            f"&lightning={BOLT11_INVOICE}&ark={ARK_ADDRESS}"
        )
        with pytest.raises(BrantaPaymentException) as exc_info:
            await service.get_payments_by_qr_code(qr)
        assert exc_info.value.reason == BrantaPaymentExceptionReason.Tampered


# ===== get_payments =====

class TestGetPayments:
    async def test_returns_payments_when_client_succeeds(self, service, client_mock):
        client_mock.get_payments.return_value = [plain_bitcoin_payment()]
        result = await service.get_payments(BITCOIN_ADDRESS)
        assert len(result.payments) == 1
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS

    async def test_returns_empty_when_client_empty(self, service, client_mock):
        client_mock.get_payments.return_value = []
        result = await service.get_payments(BITCOIN_ADDRESS)
        assert len(result.payments) == 0
        assert result.verify_url == f"http://localhost:3000/v2/verify/{BITCOIN_ADDRESS}"

    async def test_forwards_options_to_client(self, service, client_mock):
        client_mock.get_payments.return_value = [plain_bitcoin_payment()]
        await service.get_payments(BITCOIN_ADDRESS, None, LOOSE_OPTIONS)
        call_args = client_mock.get_payments.call_args
        assert call_args[0][1] == LOOSE_OPTIONS

    async def test_zk_bitcoin_address_decrypts_destination(self, service, client_mock, aes_mock):
        client_mock.get_payments.return_value = [zk_bitcoin_payment()]
        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, SECRET)
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS
        aes_mock.decrypt.assert_any_await(ENCRYPTED_BITCOIN_ADDRESS, SECRET)

    async def test_zk_bitcoin_no_key_leaves_encrypted(self, service, client_mock, aes_mock):
        client_mock.get_payments.return_value = [zk_bitcoin_payment()]
        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, None)
        assert result.payments[0].destinations[0].value == ENCRYPTED_BITCOIN_ADDRESS
        assert result.payments[0].destinations[0].is_encrypted is True
        aes_mock.decrypt.assert_not_awaited()

    async def test_zk_bitcoin_wrong_key_leaves_encrypted(self, service, client_mock, aes_mock):
        client_mock.get_payments.return_value = [zk_bitcoin_payment()]
        aes_mock.decrypt.side_effect = Exception("Decryption failed: auth tag mismatch")
        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, "wrong-key")
        assert result.payments[0].destinations[0].value == ENCRYPTED_BITCOIN_ADDRESS
        assert result.payments[0].destinations[0].is_encrypted is True

    async def test_non_zk_destination_does_not_decrypt(self, service, client_mock, aes_mock):
        client_mock.get_payments.return_value = [plain_bitcoin_payment()]
        result = await service.get_payments(BITCOIN_ADDRESS, SECRET)
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS
        aes_mock.decrypt.assert_not_awaited()

    async def test_non_zk_destination_sets_is_encrypted_false(self, service, client_mock):
        client_mock.get_payments.return_value = [plain_bitcoin_payment()]
        result = await service.get_payments(BITCOIN_ADDRESS)
        assert result.payments[0].destinations[0].is_encrypted is False

    async def test_zk_bolt11_decrypts_using_hash(self, service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [zk_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments(BOLT11_INVOICE)

        assert result.payments[0].destinations[0].value == DECRYPTED_BOLT11
        client_mock.get_payments.assert_any_await(ENCRYPTED_BOLT11, None)
        aes_mock.decrypt.assert_any_await(ENCRYPTED_BOLT11, BOLT11_HASH)

    async def test_zk_bolt11_non_bolt11_value_does_not_decrypt(self, service, client_mock, aes_mock):
        non_bolt11 = "not-a-bolt11-value"

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == non_bolt11:
                return [zk_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments(non_bolt11)
        assert result.payments[0].destinations[0].value == ENCRYPTED_BOLT11
        aes_mock.decrypt.assert_not_awaited()

    async def test_plain_bitcoin_address_sets_verify_url(self, service, client_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == BITCOIN_ADDRESS:
                return [plain_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments(BITCOIN_ADDRESS)
        assert result.verify_url == f"http://localhost:3000/v2/verify/{BITCOIN_ADDRESS}"

    async def test_zk_bitcoin_sets_verify_url_with_key_fragment(self, service, client_mock, aes_mock):
        payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).set_zk().build()
        zk_id = payment.destinations[0].zk_id

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [payment]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, SECRET)
        assert result.verify_url == f"http://localhost:3000/v2/verify/{ENCRYPTED_BITCOIN_ADDRESS}#k-{zk_id}={SECRET}"

    async def test_zk_bolt11_sets_verify_url_with_key_fragment(self, service, client_mock, aes_mock):
        payment = PaymentBuilder().add_destination(ENCRYPTED_BOLT11, DestinationType.Bolt11).set_zk().build()
        zk_id = payment.destinations[0].zk_id

        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [payment]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await service.get_payments(BOLT11_INVOICE)
        assert result.verify_url == f"http://localhost:3000/v2/verify/{ENCRYPTED_BOLT11}#k-{zk_id}={BOLT11_HASH}"

    async def test_loose_mode_bolt11_not_found_verify_url_uses_plain_value(self, service, client_mock):
        client_mock.get_payments.return_value = []

        result = await service.get_payments(BOLT11_INVOICE)

        assert len(result.payments) == 0
        assert result.verify_url == f"http://localhost:3000/v2/verify/{BOLT11_INVOICE}"
        assert client_mock.get_payments.await_count == 2


# ===== add_payment =====

class TestAddPayment:
    async def test_plain_destination_does_not_encrypt(self, service, client_mock, aes_mock):
        payment = PaymentBuilder().add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        client_mock.post_payment.return_value = plain_bitcoin_payment()

        await service.add_payment(payment)

        aes_mock.encrypt.assert_not_awaited()

    async def test_zk_bitcoin_encrypts_with_secret(self, service, client_mock, aes_mock, secret_mock):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress)
            .set_zk()
            .build()
        )
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        result = await service.add_payment(payment)

        aes_mock.encrypt.assert_any_await(BITCOIN_ADDRESS, SECRET, False)
        assert result.secret == SECRET
        assert payment.destinations[0].value == ENCRYPTED_BITCOIN_ADDRESS

    async def test_zk_bolt11_encrypts_with_hash(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(BOLT11_INVOICE, DestinationType.Bolt11)
            .set_zk()
            .build()
        )
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BOLT11, DestinationType.Bolt11).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        await service.add_payment(payment)

        aes_mock.encrypt.assert_any_await(BOLT11_INVOICE, BOLT11_HASH, True)
        assert payment.destinations[0].value == ENCRYPTED_BOLT11

    async def test_zk_ark_address_encrypts_with_hash(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(ARK_ADDRESS, DestinationType.ArkAddress)
            .set_zk()
            .build()
        )
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_ARK_ADDRESS, DestinationType.ArkAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        await service.add_payment(payment)

        aes_mock.encrypt.assert_any_await(ARK_ADDRESS, ARK_HASH, True)
        assert payment.destinations[0].value == ENCRYPTED_ARK_ADDRESS

    async def test_zk_bitcoin_sets_verify_url_with_key_fragment(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress)
            .set_zk()
            .build()
        )
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        result = await service.add_payment(payment)

        assert result.verify_url == f"http://localhost:3000/v2/verify/{ENCRYPTED_BITCOIN_ADDRESS}#k-{zk_id}={SECRET}"

    async def test_returns_generated_secret(self, service, client_mock, aes_mock):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress)
            .set_zk()
            .build()
        )
        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = payment.destinations[0].zk_id
        client_mock.post_payment.return_value = response_payment

        result = await service.add_payment(payment)
        assert result.secret == SECRET

    async def test_unsupported_zk_type_raises(self, service, client_mock):
        payment = (
            PaymentBuilder()
            .add_destination("0xdeadbeef", DestinationType.TetherAddress)
            .set_zk()
            .build()
        )
        with pytest.raises(BrantaPaymentException):
            await service.add_payment(payment)
        client_mock.post_payment.assert_not_awaited()


# ===== is_api_key_valid =====

class TestIsApiKeyValid:
    async def test_returns_true_when_client_returns_true(self, service, client_mock):
        client_mock.is_api_key_valid.return_value = True
        assert await service.is_api_key_valid() is True

    async def test_returns_false_when_client_returns_false(self, service, client_mock):
        client_mock.is_api_key_valid.return_value = False
        assert await service.is_api_key_valid() is False

    async def test_forwards_options_to_client(self, service, client_mock):
        client_mock.is_api_key_valid.return_value = True
        await service.is_api_key_valid(LOOSE_OPTIONS)
        client_mock.is_api_key_valid.assert_awaited_with(LOOSE_OPTIONS)


class TestServiceLifecycle:
    async def test_close_delegates_to_client(self, client_mock, aes_mock, secret_mock):
        client_mock.close = AsyncMock()
        svc = BrantaService(LOOSE_OPTIONS, client=client_mock, aes_encryption=aes_mock, secret_generator=secret_mock)
        await svc.close()
        client_mock.close.assert_awaited_once()

    async def test_async_context_manager(self, client_mock, aes_mock, secret_mock):
        client_mock.close = AsyncMock()
        svc = BrantaService(LOOSE_OPTIONS, client=client_mock, aes_encryption=aes_mock, secret_generator=secret_mock)
        async with svc:
            pass
        client_mock.close.assert_awaited_once()


# ===== Metadata Encryption (DEK Envelope) =====

class TestMetadataEncryption:
    DEK = "test-dek"
    ENCRYPTED_DEK = "encrypted-dek-value"
    METADATA = '{"email":"alice@example.com"}'
    ENCRYPTED_METADATA = "encrypted-metadata-value"

    async def test_add_payment_with_metadata_and_zk_bitcoin_encrypts_metadata_with_dek(
        self, service, client_mock, aes_mock, secret_mock
    ):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress)
            .set_zk()
            .build()
        )
        payment.metadata = self.METADATA
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        secret_mock.generate.side_effect = [self.DEK, SECRET]

        async def encrypt_side_effect(value, key, deterministic_nonce=False):
            if value == self.METADATA and key == self.DEK:
                return self.ENCRYPTED_METADATA
            if value == BITCOIN_ADDRESS and key == SECRET:
                return ENCRYPTED_BITCOIN_ADDRESS
            if value == self.DEK and key == SECRET:
                return self.ENCRYPTED_DEK
            return ""
        aes_mock.encrypt = AsyncMock(side_effect=encrypt_side_effect)

        await service.add_payment(payment)

        assert payment.metadata == self.ENCRYPTED_METADATA
        assert payment.destinations[0].encrypted_dek == self.ENCRYPTED_DEK
        aes_mock.encrypt.assert_any_await(self.METADATA, self.DEK, False)
        aes_mock.encrypt.assert_any_await(self.DEK, SECRET, False)

    async def test_add_payment_with_metadata_and_no_zk_leaves_metadata_plain(
        self, service, client_mock, aes_mock, secret_mock
    ):
        payment = PaymentBuilder().add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        payment.metadata = self.METADATA
        client_mock.post_payment.return_value = plain_bitcoin_payment()

        await service.add_payment(payment)

        assert payment.metadata == self.METADATA
        aes_mock.encrypt.assert_not_awaited()
        assert secret_mock.generate.call_count == 1

    async def test_add_payment_with_zk_and_no_metadata_does_not_generate_dek(
        self, service, client_mock, aes_mock, secret_mock
    ):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress)
            .set_zk()
            .build()
        )
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        async def encrypt_side_effect(value, key, deterministic_nonce=False):
            if value == BITCOIN_ADDRESS and key == SECRET:
                return ENCRYPTED_BITCOIN_ADDRESS
            return ""
        aes_mock.encrypt = AsyncMock(side_effect=encrypt_side_effect)

        await service.add_payment(payment)

        assert secret_mock.generate.call_count == 1
        assert payment.destinations[0].encrypted_dek is None

    async def test_get_payments_zk_bitcoin_with_encrypted_dek_decrypts_metadata(
        self, service, client_mock, aes_mock
    ):
        payment = Payment(
            destinations=[],
            metadata=self.ENCRYPTED_METADATA,
        )
        from branta.models import Destination
        payment.destinations = [
            Destination(
                value=ENCRYPTED_BITCOIN_ADDRESS,
                is_zk=True,
                type=DestinationType.BitcoinAddress,
                encrypted_dek=self.ENCRYPTED_DEK,
            )
        ]

        client_mock.get_payments.return_value = [payment]

        async def decrypt_side_effect(encrypted_value, key):
            if encrypted_value == ENCRYPTED_BITCOIN_ADDRESS and key == SECRET:
                return BITCOIN_ADDRESS
            if encrypted_value == self.ENCRYPTED_DEK and key == SECRET:
                return self.DEK
            if encrypted_value == self.ENCRYPTED_METADATA and key == self.DEK:
                return self.METADATA
            raise Exception(f"unexpected: decrypt({encrypted_value}, {key})")
        aes_mock.decrypt = AsyncMock(side_effect=decrypt_side_effect)

        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, SECRET)

        assert result.payments[0].metadata == self.METADATA
        assert result.payments[0].is_metadata_decrypted is True

    async def test_get_payments_wrong_key_leaves_metadata_encrypted(
        self, service, client_mock, aes_mock
    ):
        from branta.models import Destination
        payment = Payment(
            destinations=[
                Destination(
                    value=ENCRYPTED_BITCOIN_ADDRESS,
                    is_zk=True,
                    type=DestinationType.BitcoinAddress,
                    encrypted_dek=self.ENCRYPTED_DEK,
                )
            ],
            metadata=self.ENCRYPTED_METADATA,
        )

        client_mock.get_payments.return_value = [payment]

        async def decrypt_side_effect(encrypted_value, key):
            if encrypted_value == ENCRYPTED_BITCOIN_ADDRESS and key == SECRET:
                return BITCOIN_ADDRESS
            raise Exception("Decryption failed: auth tag mismatch")
        aes_mock.decrypt = AsyncMock(side_effect=decrypt_side_effect)

        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, SECRET)
        assert result.payments[0].metadata == self.ENCRYPTED_METADATA
        assert not result.payments[0].is_metadata_decrypted

    async def test_get_payments_two_zk_destinations_decrypts_metadata_once(
        self, service, client_mock, aes_mock
    ):
        from branta.models import Destination
        ENCRYPTED_BITCOIN_ADDRESS2 = "encrypted-bitcoin-address-2"
        payment = Payment(
            destinations=[
                Destination(value=ENCRYPTED_BITCOIN_ADDRESS, is_zk=True, type=DestinationType.BitcoinAddress, encrypted_dek=self.ENCRYPTED_DEK),
                Destination(value=ENCRYPTED_BITCOIN_ADDRESS2, is_zk=True, type=DestinationType.BitcoinAddress, encrypted_dek=self.ENCRYPTED_DEK),
            ],
            metadata=self.ENCRYPTED_METADATA,
        )

        client_mock.get_payments.return_value = [payment]
        metadata_decrypt_count = 0

        async def decrypt_side_effect(encrypted_value, key):
            nonlocal metadata_decrypt_count
            if encrypted_value in (ENCRYPTED_BITCOIN_ADDRESS, ENCRYPTED_BITCOIN_ADDRESS2) and key == SECRET:
                return BITCOIN_ADDRESS
            if encrypted_value == self.ENCRYPTED_DEK and key == SECRET:
                return self.DEK
            if encrypted_value == self.ENCRYPTED_METADATA and key == self.DEK:
                metadata_decrypt_count += 1
                return self.METADATA
            raise Exception(f"unexpected: decrypt({encrypted_value}, {key})")
        aes_mock.decrypt = AsyncMock(side_effect=decrypt_side_effect)

        result = await service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, SECRET)
        assert result.payments[0].metadata == self.METADATA
        assert metadata_decrypt_count == 1


# ===== Strict Mode =====

class TestStrictMode:
    async def test_get_payments_strict_bitcoin_address_throws(self, strict_service, client_mock):
        with pytest.raises(BrantaPaymentException):
            await strict_service.get_payments(BITCOIN_ADDRESS)
        client_mock.get_payments.assert_not_awaited()

    async def test_get_payments_strict_encrypted_bitcoin_with_secret_decrypts(
        self, strict_service, client_mock, aes_mock
    ):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await strict_service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, SECRET)

        assert len(result.payments) == 1
        assert result.payments[0].destinations[0].value == BITCOIN_ADDRESS
        assert result.payments[0].destinations[0].is_encrypted is False

    async def test_get_payments_strict_encrypted_bitcoin_wrong_key_leaves_encrypted(
        self, strict_service, client_mock, aes_mock
    ):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)
        aes_mock.decrypt.side_effect = Exception("Decryption failed: auth tag mismatch")

        result = await strict_service.get_payments(ENCRYPTED_BITCOIN_ADDRESS, "wrong-key")

        assert result.payments[0].destinations[0].value == ENCRYPTED_BITCOIN_ADDRESS
        assert result.payments[0].destinations[0].is_encrypted is True

    async def test_get_payments_strict_bolt11_does_not_throw(self, strict_service, client_mock, aes_mock):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [zk_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        await strict_service.get_payments(BOLT11_INVOICE)
        client_mock.get_payments.assert_any_await(ENCRYPTED_BOLT11, None)

    async def test_get_payments_strict_bolt11_no_fallback_to_plain_text(
        self, strict_service, client_mock
    ):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return []
            if lookup == BOLT11_INVOICE:
                return [plain_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        result = await strict_service.get_payments(BOLT11_INVOICE)

        assert len(result.payments) == 0
        assert result.verify_url == f"http://localhost:3000/v2/verify/{ENCRYPTED_BOLT11}"
        calls = [c[0][0] for c in client_mock.get_payments.call_args_list]
        assert BOLT11_INVOICE not in calls

    async def test_get_payments_by_qr_code_strict_plain_bitcoin_uri_returns_empty(
        self, strict_service, client_mock
    ):
        result = await strict_service.get_payments_by_qr_code(f"bitcoin:{BITCOIN_ADDRESS}")

        assert len(result.payments) == 0
        assert result.verify_url == f"http://localhost:3000/v2/verify/{BITCOIN_ADDRESS}"
        client_mock.get_payments.assert_not_awaited()

    async def test_get_payments_by_qr_code_strict_zk_bitcoin_uri_succeeds(
        self, strict_service, client_mock, aes_mock
    ):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BITCOIN_ADDRESS:
                return [zk_bitcoin_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        qr = f"bitcoin:{BITCOIN_ADDRESS}?branta_id={ENCRYPTED_BITCOIN_ADDRESS}&branta_secret={SECRET}"
        result = await strict_service.get_payments_by_qr_code(qr)

        assert len(result.payments) == 1
        client_mock.get_payments.assert_awaited_with(ENCRYPTED_BITCOIN_ADDRESS, None)

    async def test_get_payments_by_qr_code_strict_lightning_bolt11_succeeds(
        self, strict_service, client_mock, aes_mock
    ):
        async def get_side_effect(lookup, opts=None, signal=None):
            if lookup == ENCRYPTED_BOLT11:
                return [plain_bolt11_payment()]
            return []
        client_mock.get_payments = AsyncMock(side_effect=get_side_effect)

        await strict_service.get_payments_by_qr_code(f"lightning:{BOLT11_INVOICE}")
        client_mock.get_payments.assert_awaited_with(ENCRYPTED_BOLT11, None)

    async def test_add_payment_strict_plain_destination_throws(self, strict_service, client_mock):
        payment = PaymentBuilder().add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        with pytest.raises(BrantaPaymentException):
            await strict_service.add_payment(payment)
        client_mock.post_payment.assert_not_awaited()

    async def test_add_payment_strict_all_zk_destinations_succeeds(
        self, strict_service, client_mock, aes_mock
    ):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress)
            .set_zk()
            .build()
        )
        zk_id = payment.destinations[0].zk_id

        response_payment = PaymentBuilder().add_destination(ENCRYPTED_BITCOIN_ADDRESS, DestinationType.BitcoinAddress).build()
        response_payment.destinations[0].is_zk = True
        response_payment.destinations[0].zk_id = zk_id
        client_mock.post_payment.return_value = response_payment

        await strict_service.add_payment(payment)
        client_mock.post_payment.assert_awaited_once()

    async def test_add_payment_strict_mixed_destinations_throws(self, strict_service, client_mock):
        payment = (
            PaymentBuilder()
            .add_destination(BITCOIN_ADDRESS, DestinationType.BitcoinAddress).set_zk()
            .add_destination(BOLT11_INVOICE, DestinationType.Bolt11)
            .build()
        )
        with pytest.raises(BrantaPaymentException):
            await strict_service.add_payment(payment)
        client_mock.post_payment.assert_not_awaited()
