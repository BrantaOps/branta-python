from __future__ import annotations

import json

import pytest

from branta.enums import BrantaEnvironment, DestinationType, VerifyStatus
from branta.exceptions import BrantaPaymentException, IncompleteError
from branta.extensions import to_normalized_hash
from branta.models import Destination, Payment
from branta.options import BrantaApiOptions
from branta.encryption import AesEncryption
from branta.service import BrantaService

ADDRESS = "bc1qmerchant"
SECRET = "branta-secret"
LOOKUP = "lookup-token"
INVOICE = "lnbc100n1ptest"


class FakeClient:
    def __init__(self) -> None:
        self.gets: list[str] = []
        self.posts: list[Payment] = []
        self.payments: list[Payment] = []
        self.get_error: Exception | None = None
        self.post_error: Exception | None = None
        self.post_result: Payment | None | str = "echo"

    async def get_payments(self, destination_value: str, options=None):
        del options
        self.gets.append(destination_value)
        if self.get_error is not None:
            raise self.get_error
        return self.payments

    async def post_payment(self, payment: Payment, options=None):
        del options
        self.posts.append(payment)
        if self.post_error is not None:
            raise self.post_error
        if self.post_result == "echo":
            return payment
        return self.post_result

    async def is_api_key_valid(self, options=None) -> bool:
        del options
        return True


class ScriptedSecrets:
    deterministic_nonce = False

    def __init__(self, values: list[str]) -> None:
        self._values = list(values)

    def generate(self) -> str:
        return self._values.pop(0)


def service(client: FakeClient, secrets: list[str] | None = None) -> BrantaService:
    return BrantaService(
        BrantaApiOptions(environment=BrantaEnvironment.Localhost, api_key="key"),
        client=client,  # type: ignore[arg-type]
        secret_generator=ScriptedSecrets(secrets or ["unused"]),  # type: ignore[arg-type]
    )


def qr(address: str = ADDRESS, secret: str = SECRET, lookup: str = LOOKUP) -> str:
    return f"bitcoin:{address}?branta_id={lookup}&branta_secret={secret}"


async def encrypted_address(address: str = ADDRESS, secret: str = SECRET, destination_id: str = "dest-1") -> Payment:
    ciphertext = await AesEncryption.encrypt(address, secret)
    return Payment(
        destinations=[
            Destination(value=ciphertext, type=DestinationType.BitcoinAddress, id=destination_id),
        ]
    )


class TestVerify:
    async def test_match_decrypts_the_address_and_returns_the_key_fragment(self):
        client = FakeClient()
        client.payments = [await encrypted_address()]
        result = await service(client).verify(qr())

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].destinations[0].value == ADDRESS
        assert result.verify_url == f"http://localhost:3000/v2/verify/{LOOKUP}#k-dest-1={SECRET}"
        assert client.gets == [LOOKUP]

    async def test_swapped_address_is_tampered_without_payments_or_key_fragment(self):
        client = FakeClient()
        stored = await encrypted_address()
        client.payments = [stored]
        result = await service(client).verify(qr(address="bc1qattacker"))

        assert result.status == VerifyStatus.Tampered
        assert result.payments is None
        assert "#k-" not in result.verify_url
        assert result.verify_url.endswith(f"/v2/verify/{LOOKUP}")
        assert stored.destinations[0].value != "bc1qattacker"

    async def test_wrong_secret_is_unknown(self):
        client = FakeClient()
        client.payments = [await encrypted_address()]
        result = await service(client).verify(qr(secret="wrong-secret"))

        assert result.status == VerifyStatus.Unknown
        assert result.payments is None
        assert "#k-" not in result.verify_url

    async def test_bare_address_is_unknown_and_does_not_get(self):
        client = FakeClient()
        for raw in (ADDRESS, f"bitcoin:{ADDRESS}", "tb1qtest", "bcrt1qtest"):
            result = await service(client).verify(raw)
            assert result.status == VerifyStatus.Unknown
            assert result.payments is None
        assert client.gets == []

    async def test_branta_params_without_a_payable_destination_do_not_get(self):
        client = FakeClient()
        result = await service(client).verify(f"bitcoin:?branta_id={LOOKUP}&branta_secret={SECRET}")

        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    async def test_lno_pay_and_bolt12_are_unknown_without_a_lookup(self):
        client = FakeClient()
        for raw in (
            f"bitcoin:{ADDRESS}?lno=lno1qqexample",
            f"bitcoin:{ADDRESS}?pay=bitcoin:bc1qother",
            f"bitcoin:{ADDRESS}?bolt12=lno1qqexample",
            "lightning:lnotest",
        ):
            result = await service(client).verify(raw)
            assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    async def test_conflicting_on_chain_addresses_are_tampered_without_a_lookup(self):
        client = FakeClient()
        result = await service(client).verify("bitcoin:?bc=bc1qone&tb=tb1qtwo")

        assert result.status == VerifyStatus.Tampered
        assert client.gets == []

    async def test_bech32_match_is_case_insensitive(self):
        client = FakeClient()
        client.payments = [await encrypted_address()]
        result = await service(client).verify(qr(address=ADDRESS.upper()))

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].destinations[0].value == ADDRESS

    async def test_bolt11_must_decrypt_to_match(self):
        key = to_normalized_hash(INVOICE)
        ciphertext = await AesEncryption.encrypt(INVOICE, key, True)
        client = FakeClient()
        client.payments = [
            Payment(destinations=[Destination(value=ciphertext, type=DestinationType.Bolt11, id="bolt-1")])
        ]
        result = await service(client).verify(f"lightning:{INVOICE}")

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].destinations[0].value == INVOICE
        assert client.gets == [ciphertext]
        assert f"#k-bolt-1={key}" in result.verify_url

    async def test_bolt11_hit_that_does_not_decrypt_is_unknown(self):
        client = FakeClient()
        client.payments = [
            Payment(
                destinations=[
                    Destination(value="not-the-invoice", type=DestinationType.Bolt11, id="bolt-1"),
                ]
            )
        ]
        result = await service(client).verify(f"lightning:{INVOICE}")

        assert result.status == VerifyStatus.Unknown
        assert result.payments is None
        assert len(client.gets) == 1

    async def test_extra_lightning_leg_that_does_not_decrypt_is_unknown(self):
        client = FakeClient()
        client.payments = [await encrypted_address()]
        result = await service(client).verify(f"{qr()}&lightning={INVOICE}")

        assert result.status == VerifyStatus.Unknown
        assert result.payments is None
        assert client.gets == [LOOKUP]

    async def test_404_is_unknown(self):
        client = FakeClient()
        result = await service(client).verify(f"lightning:{INVOICE}")

        assert result.status == VerifyStatus.Unknown
        assert result.payments is None

    async def test_server_error_is_incomplete(self):
        client = FakeClient()
        client.get_error = IncompleteError("InternalServerError")
        result = await service(client).verify(qr())

        assert result.status == VerifyStatus.Incomplete
        assert result.payments is None
        assert result.verify_url.endswith(f"/v2/verify/{LOOKUP}")

    async def test_description_is_lifted_from_decrypted_metadata(self):
        dek = "dek-1"
        metadata = json.dumps({"description": "Invoice #123"})
        encrypted_metadata = await AesEncryption.encrypt(metadata, dek)
        encrypted_dek = await AesEncryption.encrypt(dek, SECRET)
        ciphertext = await AesEncryption.encrypt(ADDRESS, SECRET)
        client = FakeClient()
        client.payments = [
            Payment(
                metadata=encrypted_metadata,
                destinations=[
                    Destination(
                        value=ciphertext,
                        type=DestinationType.BitcoinAddress,
                        id="dest-1",
                        encrypted_dek=encrypted_dek,
                    )
                ],
            )
        ]
        result = await service(client).verify(qr())

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].description == "Invoice #123"


class TestAddPayment:
    async def test_posts_a_copy_and_leaves_the_caller_plaintext(self):
        client = FakeClient()
        payment = Payment(
            description="Invoice #1",
            destinations=[Destination(value=ADDRESS, type=DestinationType.BitcoinAddress, id="dest-1")],
        )
        result = await service(client, ["dek-1", SECRET]).add_payment(payment)

        assert payment.description == "Invoice #1"
        assert payment.destinations[0].value == ADDRESS
        assert payment.metadata is None
        posted = client.posts[0]
        assert posted is not payment
        assert posted.description is None
        assert posted.destinations[0].value != ADDRESS
        assert await AesEncryption.decrypt(posted.destinations[0].value, SECRET) == ADDRESS
        metadata = await AesEncryption.decrypt(posted.metadata or "", "dek-1")
        assert json.loads(metadata)["description"] == "Invoice #1"
        assert result.secret == SECRET
        assert f"#k-dest-1={SECRET}" in result.verify_url

    async def test_retry_after_post_failure_encrypts_the_original_address(self):
        client = FakeClient()
        client.post_error = BrantaPaymentException("InternalServerError")
        payment = Payment(
            destinations=[Destination(value=ADDRESS, type=DestinationType.BitcoinAddress, id="dest-1")],
        )
        branta = service(client, ["secret-1", "secret-2"])

        with pytest.raises(BrantaPaymentException):
            await branta.add_payment(payment)
        client.post_error = None
        await branta.add_payment(payment)

        assert payment.destinations[0].value == ADDRESS
        first = await AesEncryption.decrypt(client.posts[0].destinations[0].value, "secret-1")
        second = await AesEncryption.decrypt(client.posts[1].destinations[0].value, "secret-2")
        assert first == ADDRESS
        assert second == ADDRESS
        assert client.posts[0].destinations[0].value != client.posts[1].destinations[0].value

    async def test_retry_after_post_failure_bolt11_still_encrypts_the_invoice(self):
        client = FakeClient()
        client.post_error = BrantaPaymentException("InternalServerError")
        payment = Payment(
            destinations=[Destination(value=INVOICE, type=DestinationType.Bolt11, id="bolt-1")],
        )
        branta = service(client, ["secret-1", "secret-2"])
        expected = await AesEncryption.encrypt(INVOICE, to_normalized_hash(INVOICE), True)

        with pytest.raises(BrantaPaymentException):
            await branta.add_payment(payment)
        client.post_error = None
        await branta.add_payment(payment)

        assert payment.destinations[0].value == INVOICE
        assert client.posts[0].destinations[0].value == expected
        assert client.posts[1].destinations[0].value == expected

    async def test_infers_bitcoin_address_when_type_is_omitted(self):
        client = FakeClient()
        payment = Payment(destinations=[Destination(value=ADDRESS, id="dest-1")])
        await service(client, [SECRET]).add_payment(payment)

        assert client.posts[0].destinations[0].type == DestinationType.BitcoinAddress
        assert await AesEncryption.decrypt(client.posts[0].destinations[0].value, SECRET) == ADDRESS

    async def test_type_that_cannot_be_encrypted_throws_before_post(self):
        client = FakeClient()
        payment = Payment(destinations=[Destination(value="not-a-destination")])

        with pytest.raises(BrantaPaymentException, match="cannot be encrypted"):
            await service(client).add_payment(payment)
        assert client.posts == []
        assert payment.destinations[0].value == "not-a-destination"

    async def test_empty_response_throws_and_leaves_the_caller_unchanged(self):
        client = FakeClient()
        client.post_result = None
        payment = Payment(
            destinations=[Destination(value=ADDRESS, type=DestinationType.BitcoinAddress, id="dest-1")],
        )

        with pytest.raises(BrantaPaymentException, match="No payment returned"):
            await service(client, [SECRET]).add_payment(payment)
        assert payment.destinations[0].value == ADDRESS
