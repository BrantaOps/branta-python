from __future__ import annotations

import json
from urllib.parse import quote

import pytest

from branta.enums import EVM_TOKEN_RAILS, BrantaEnvironment, DestinationType, VerifyStatus
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
            Destination(
                value=ciphertext,
                type=DestinationType.BitcoinAddress,
                id=destination_id,
                is_encrypted=True,
            ),
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
        assert result.matched_destinations is not None
        assert len(result.matched_destinations) == 1
        assert result.matched_destinations[0].type == DestinationType.BitcoinAddress
        assert result.matched_destinations[0].value == ADDRESS
        assert result.verify_url == f"http://localhost:3000/v2/verify/{LOOKUP}#k-dest-1={SECRET}"
        assert client.gets == [LOOKUP]

    async def test_verify_url_encodes_reserved_characters_in_the_fragment(self):
        client = FakeClient()
        secret = "secret&injected=1"
        client.payments = [await encrypted_address(secret=secret, destination_id="AAAA&k-BBBB")]
        result = await service(client).verify(qr(secret=quote(secret, safe="")))

        assert result.status == VerifyStatus.Match
        assert result.verify_url.endswith("#k-AAAA%26k-BBBB=secret%26injected%3D1")

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

    async def test_bolt11_decrypting_to_a_different_invoice_is_tampered(self):
        key = to_normalized_hash(INVOICE)
        attacker = "lnbc1attacker"
        ciphertext = await AesEncryption.encrypt(attacker, key)
        client = FakeClient()
        client.payments = [
            Payment(
                destinations=[
                    Destination(value="copied-lookup", type=DestinationType.BitcoinAddress, id="btc"),
                    Destination(value=ciphertext, type=DestinationType.Bolt11, id="bolt"),
                ]
            )
        ]
        result = await service(client).verify(f"lightning:{INVOICE}")

        assert result.status == VerifyStatus.Tampered
        assert result.payments is None
        assert "#k-" not in result.verify_url

    async def test_bolt11_match_is_case_insensitive(self):
        key = to_normalized_hash(INVOICE)
        ciphertext = await AesEncryption.encrypt(INVOICE.lower(), key, True)
        client = FakeClient()
        client.payments = [
            Payment(destinations=[Destination(value=ciphertext, type=DestinationType.Bolt11, id="bolt-1")])
        ]
        result = await service(client).verify(f"lightning:{INVOICE.upper()}")

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].destinations[0].value == INVOICE.lower()

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


USDT_POLYGON = "0x278297528c32eCa01295B0d2135984d3442ec963"
USDC_POLYGON = "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"
SIBLING_USDT = "0x2222222222222222222222222222222222222222"
SWAPPED_POLYGON = "0x1111111111111111111111111111111111111111"
SWAPPED_EVM = "0x" + "f" * 40


def rail_for(destination_type: DestinationType):
    return next(rail for rail in EVM_TOKEN_RAILS if rail.type == destination_type)


def transfer_uri(
    destination_type: DestinationType,
    address: str,
    encrypted: str,
    secret: str = SECRET,
    amount: str = "1000000",
) -> str:
    """ERC-681 transfer URI for one rail. Chain id and contract come from the rail table."""
    rail = rail_for(destination_type)
    return (
        f"ethereum:{rail.contract}@{rail.chain_id}/transfer?address={address}&uint256={amount}"
        f"&branta_id={quote(encrypted, safe='')}&branta_secret={quote(secret, safe='')}"
    )


def polygon_usdt_uri(address: str, encrypted: str, secret: str = SECRET) -> str:
    return transfer_uri(DestinationType.UsdtPolygon, address, encrypted, secret)


def polygon_usdc_uri(address: str, encrypted: str, secret: str = SECRET) -> str:
    return transfer_uri(DestinationType.UsdcPolygon, address, encrypted, secret)


async def encrypted_secret_key_rail(
    address: str,
    destination_type: DestinationType,
    secret: str = SECRET,
    destination_id: str = "zk-rail",
) -> Destination:
    ciphertext = await AesEncryption.encrypt(address, secret)
    return Destination(
        value=ciphertext,
        type=destination_type,
        id=destination_id,
        is_encrypted=True,
    )


class TestPolygonVerify:
    async def test_usdt_match_ignores_amount_and_sets_matched_destinations(self):
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, dest.value))

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].destinations[0].type == DestinationType.UsdtPolygon
        assert result.payments[0].destinations[0].value == USDT_POLYGON
        assert result.matched_destinations is not None
        assert len(result.matched_destinations) == 1
        assert result.matched_destinations[0].type == DestinationType.UsdtPolygon

    async def test_amount_is_not_part_of_the_match(self):
        for amount in ("1", "50000000", "999999999999"):
            dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon)
            client = FakeClient()
            client.payments = [Payment(destinations=[dest])]
            result = await service(client).verify(
                transfer_uri(DestinationType.UsdtPolygon, USDT_POLYGON, dest.value, amount=amount)
            )
            assert result.status == VerifyStatus.Match

    async def test_usdt_case_insensitive_match(self):
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon)
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON.lower(), dest.value))
        assert result.status == VerifyStatus.Match

    async def test_usdt_0x_prefix_case_insensitive_match(self):
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon)
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        mixed = "0X" + USDT_POLYGON[2:]
        result = await service(client).verify(polygon_usdt_uri(mixed, dest.value))
        assert result.status == VerifyStatus.Match

    async def test_usdt_swapped_is_tampered(self):
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon)
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdt_uri(SWAPPED_POLYGON, dest.value))
        assert result.status == VerifyStatus.Tampered
        assert result.payments is None

    async def test_bare_usdt_address_is_unknown(self):
        client = FakeClient()
        result = await service(client).verify(USDT_POLYGON)
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    async def test_transfer_without_branta_params_is_unknown(self):
        client = FakeClient()
        rail = rail_for(DestinationType.UsdtPolygon)
        result = await service(client).verify(
            f"ethereum:{rail.contract}@{rail.chain_id}/transfer?address={USDT_POLYGON}&uint256=50000000"
        )
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    async def test_polygon_ignores_sibling_bitcoin_rail(self):
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        btc = await encrypted_address()
        client = FakeClient()
        client.payments = [Payment(destinations=[btc.destinations[0], usdt])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, usdt.value))
        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].type == DestinationType.BitcoinAddress
        assert dests[0].is_encrypted is True
        assert dests[1].is_encrypted is False
        assert dests[1].value == USDT_POLYGON

    async def test_bitcoin_ignores_sibling_usdt_rail(self):
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        btc = await encrypted_address()
        client = FakeClient()
        client.payments = [Payment(destinations=[btc.destinations[0], usdt])]
        result = await service(client).verify(qr())
        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].is_encrypted is False
        assert dests[0].value == ADDRESS
        assert dests[1].is_encrypted is True
        assert dests[1].type == DestinationType.UsdtPolygon

    async def test_derived_key_only_branta_qr_leaves_secret_key_rails_encrypted(self):
        key = to_normalized_hash(INVOICE)
        bolt_cipher = await AesEncryption.encrypt(INVOICE, key, True)
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        client = FakeClient()
        client.payments = [
            Payment(
                destinations=[
                    Destination(
                        value=bolt_cipher,
                        type=DestinationType.Bolt11,
                        id="bolt-1",
                        is_encrypted=True,
                    ),
                    usdt,
                ]
            )
        ]
        result = await service(client).verify(
            f"bitcoin:?lightning={INVOICE}&branta_id={LOOKUP}&branta_secret={SECRET}"
        )
        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].is_encrypted is False
        assert dests[0].value == INVOICE
        assert dests[1].is_encrypted is True
        assert dests[1].type == DestinationType.UsdtPolygon
        assert len(result.matched_destinations) == 1
        assert result.matched_destinations[0].type == DestinationType.Bolt11

    async def test_matched_destinations_are_copies(self):
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, dest.value))
        assert result.status == VerifyStatus.Match
        result.matched_destinations[0].value = "mutated"
        assert result.payments[0].destinations[0].value == USDT_POLYGON

    async def test_swapped_still_tampered_with_sibling_bitcoin(self):
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        btc = await encrypted_address()
        client = FakeClient()
        client.payments = [Payment(destinations=[btc.destinations[0], usdt])]
        result = await service(client).verify(polygon_usdt_uri(SWAPPED_POLYGON, usdt.value))
        assert result.status == VerifyStatus.Tampered

    async def test_second_usdt_destination_with_another_address_stays_encrypted(self):
        match = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        sibling = await encrypted_secret_key_rail(SIBLING_USDT, DestinationType.UsdtPolygon, destination_id="zk-sib")
        client = FakeClient()
        client.payments = [Payment(destinations=[sibling, match])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, match.value))
        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].is_encrypted is True
        assert dests[0].value == sibling.value
        assert dests[1].is_encrypted is False
        assert dests[1].value == USDT_POLYGON

    async def test_swapped_is_tampered_when_no_destination_of_the_type_matches(self):
        match = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        sibling = await encrypted_secret_key_rail(SIBLING_USDT, DestinationType.UsdtPolygon, destination_id="zk-sib")
        client = FakeClient()
        client.payments = [Payment(destinations=[sibling, match])]
        result = await service(client).verify(polygon_usdt_uri(SWAPPED_POLYGON, match.value))
        assert result.status == VerifyStatus.Tampered

    async def test_usdc_match(self):
        dest = await encrypted_secret_key_rail(USDC_POLYGON, DestinationType.UsdcPolygon, destination_id="zk-usdc")
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdc_uri(USDC_POLYGON, dest.value))
        assert result.status == VerifyStatus.Match
        assert result.matched_destinations[0].type == DestinationType.UsdcPolygon

    async def test_usdc_swapped_is_tampered(self):
        dest = await encrypted_secret_key_rail(USDC_POLYGON, DestinationType.UsdcPolygon, destination_id="zk-usdc")
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdc_uri(SWAPPED_POLYGON, dest.value))
        assert result.status == VerifyStatus.Tampered

    async def test_usdt_scan_binds_usdt_leaves_usdc_encrypted(self):
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        usdc = await encrypted_secret_key_rail(USDC_POLYGON, DestinationType.UsdcPolygon, destination_id="zk-usdc")
        client = FakeClient()
        client.payments = [Payment(destinations=[usdt, usdc])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, usdt.value))
        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].is_encrypted is False and dests[0].type == DestinationType.UsdtPolygon
        assert dests[1].is_encrypted is True and dests[1].type == DestinationType.UsdcPolygon

    async def test_usdc_scan_binds_usdc_leaves_usdt_encrypted(self):
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        usdc = await encrypted_secret_key_rail(USDC_POLYGON, DestinationType.UsdcPolygon, destination_id="zk-usdc")
        client = FakeClient()
        client.payments = [Payment(destinations=[usdt, usdc])]
        result = await service(client).verify(polygon_usdc_uri(USDC_POLYGON, usdc.value))
        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].is_encrypted is True and dests[0].type == DestinationType.UsdtPolygon
        assert dests[1].is_encrypted is False and dests[1].type == DestinationType.UsdcPolygon

    async def test_wrong_secret_is_unknown(self):
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon)
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, dest.value, secret="wrong-secret"))
        assert result.status == VerifyStatus.Unknown

    async def test_same_address_usdt_and_usdc_binds_only_the_scanned_token(self):
        usdt = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        usdc = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdcPolygon, destination_id="zk-usdc")
        client = FakeClient()
        client.payments = [Payment(destinations=[usdt, usdc])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, usdt.value))
        assert result.status == VerifyStatus.Match
        assert [d.type for d in result.matched_destinations] == [DestinationType.UsdtPolygon]
        assert result.payments[0].destinations[1].is_encrypted is True

    async def test_description_is_lifted_from_decrypted_metadata(self):
        dek = "dek-poly"
        metadata = json.dumps({"description": "USDT invoice"})
        encrypted_metadata = await AesEncryption.encrypt(metadata, dek)
        encrypted_dek = await AesEncryption.encrypt(dek, SECRET)
        dest = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-usdt")
        dest.encrypted_dek = encrypted_dek
        client = FakeClient()
        client.payments = [Payment(metadata=encrypted_metadata, destinations=[dest])]
        result = await service(client).verify(polygon_usdt_uri(USDT_POLYGON, dest.value))

        assert result.status == VerifyStatus.Match
        assert result.payments is not None
        assert result.payments[0].description == "USDT invoice"
        assert result.matched_destinations is not None
        assert result.matched_destinations[0].type == DestinationType.UsdtPolygon

    async def test_add_payment_encrypts_usdt_and_usdc_polygon(self):
        client = FakeClient()
        caller = Payment(destinations=[Destination(value=USDT_POLYGON, type=DestinationType.UsdtPolygon, id="zk-1")])
        result = await service(client, ["polygon-secret"]).add_payment(caller)
        assert caller.destinations[0].value == USDT_POLYGON
        assert client.posts[0].destinations[0].value != USDT_POLYGON
        assert client.posts[0].destinations[0].type == DestinationType.UsdtPolygon
        assert result.secret == "polygon-secret"

        usdc_client = FakeClient()
        await service(usdc_client, ["polygon-secret"]).add_payment(
            Payment(destinations=[Destination(value=USDC_POLYGON, type=DestinationType.UsdcPolygon, id="zk-1")])
        )
        assert usdc_client.posts[0].destinations[0].type == DestinationType.UsdcPolygon
        assert usdc_client.posts[0].destinations[0].value != USDC_POLYGON

    async def test_add_payment_bare_ox_without_type_is_unsupported(self):
        client = FakeClient()
        with pytest.raises(BrantaPaymentException, match="cannot be encrypted"):
            await service(client).add_payment(Payment(destinations=[Destination(value=USDT_POLYGON)]))
        assert client.posts == []

    async def test_add_payment_polygon_with_description_encrypts_dek(self):
        client = FakeClient()
        payment = Payment(
            description="Polygon invoice",
            destinations=[Destination(value=USDT_POLYGON, type=DestinationType.UsdtPolygon, id="zk-1")],
        )
        result = await service(client, ["dek-poly", "polygon-secret"]).add_payment(payment)

        assert payment.description == "Polygon invoice"
        assert payment.destinations[0].value == USDT_POLYGON
        posted = client.posts[0]
        assert posted.description is None
        assert posted.destinations[0].encrypted_dek is not None
        assert await AesEncryption.decrypt(posted.destinations[0].value, "polygon-secret") == USDT_POLYGON
        dek = await AesEncryption.decrypt(posted.destinations[0].encrypted_dek, "polygon-secret")
        assert dek == "dek-poly"
        metadata = await AesEncryption.decrypt(posted.metadata or "", dek)
        assert json.loads(metadata)["description"] == "Polygon invoice"
        assert result.secret == "polygon-secret"


USDT_TRON = "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"
USDT_TON = "EQDtFpEwcFAEcRe5mLVh2N6C0y-_tur3BYOM93pEZPw390by"
USDT_SOLANA = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
USDC_SOLANA = "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDofycyinf"

# One fresh deposit per rail so a payment holding two rails never shares an address.
RAIL_DEPOSITS = {
    rail.type: "0x" + format(index + 1, "x").rjust(40, "1")
    for index, rail in enumerate(EVM_TOKEN_RAILS)
}


class TestEvmRailVerify:
    @pytest.mark.parametrize("rail", EVM_TOKEN_RAILS, ids=lambda rail: rail.type.value)
    async def test_match_returns_the_scanned_type(self, rail):
        deposit = RAIL_DEPOSITS[rail.type]
        dest = await encrypted_secret_key_rail(deposit, rail.type, destination_id="zk-rail")
        ciphertext = dest.value
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(transfer_uri(rail.type, deposit, ciphertext))

        assert result.status == VerifyStatus.Match
        assert result.matched_destinations is not None
        assert [d.type for d in result.matched_destinations] == [rail.type]
        assert result.matched_destinations[0].value == deposit
        assert client.gets == [ciphertext]

    @pytest.mark.parametrize("rail", EVM_TOKEN_RAILS, ids=lambda rail: rail.type.value)
    async def test_lowercase_deposit_still_matches(self, rail):
        deposit = RAIL_DEPOSITS[rail.type]
        dest = await encrypted_secret_key_rail(deposit.upper().replace("0X", "0x"), rail.type)
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(transfer_uri(rail.type, deposit.lower(), dest.value))
        assert result.status == VerifyStatus.Match

    @pytest.mark.parametrize("rail", EVM_TOKEN_RAILS, ids=lambda rail: rail.type.value)
    async def test_swapped_deposit_is_tampered(self, rail):
        deposit = RAIL_DEPOSITS[rail.type]
        dest = await encrypted_secret_key_rail(deposit, rail.type)
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        result = await service(client).verify(transfer_uri(rail.type, SWAPPED_EVM, dest.value))
        assert result.status == VerifyStatus.Tampered
        assert result.payments is None
        assert "#k-" not in result.verify_url

    @pytest.mark.parametrize("rail", EVM_TOKEN_RAILS, ids=lambda rail: rail.type.value)
    async def test_wrong_chain_id_is_unknown_without_get(self, rail):
        deposit = RAIL_DEPOSITS[rail.type]
        other_chain = 137 if rail.chain_id != 137 else 1
        client = FakeClient()
        result = await service(client).verify(
            f"ethereum:{rail.contract}@{other_chain}/transfer?address={deposit}&branta_id=abc&branta_secret={SECRET}"
        )
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    @pytest.mark.parametrize("rail", EVM_TOKEN_RAILS, ids=lambda rail: rail.type.value)
    async def test_transfer_without_branta_params_is_unknown_without_get(self, rail):
        deposit = RAIL_DEPOSITS[rail.type]
        client = FakeClient()
        result = await service(client).verify(
            f"ethereum:{rail.contract}@{rail.chain_id}/transfer?address={deposit}&uint256=1"
        )
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    async def test_usdc_scan_against_a_usdt_only_payment_is_unknown(self):
        usdt_deposit = RAIL_DEPOSITS[DestinationType.UsdtEthereum]
        usdt = await encrypted_secret_key_rail(usdt_deposit, DestinationType.UsdtEthereum, destination_id="zk-usdt")
        client = FakeClient()
        client.payments = [Payment(destinations=[usdt])]
        result = await service(client).verify(
            transfer_uri(DestinationType.UsdcEthereum, usdt_deposit, usdt.value)
        )
        assert result.status == VerifyStatus.Unknown
        assert result.payments is None
        assert client.payments[0].destinations[0].is_encrypted is True

    async def test_dual_token_payment_binds_only_the_scanned_token(self):
        usdt_deposit = RAIL_DEPOSITS[DestinationType.UsdtEthereum]
        usdc_deposit = RAIL_DEPOSITS[DestinationType.UsdcEthereum]

        async def fresh() -> tuple[FakeClient, str]:
            usdt = await encrypted_secret_key_rail(usdt_deposit, DestinationType.UsdtEthereum, destination_id="zk-usdt")
            usdc = await encrypted_secret_key_rail(usdc_deposit, DestinationType.UsdcEthereum, destination_id="zk-usdc")
            client = FakeClient()
            client.payments = [Payment(destinations=[usdt, usdc])]
            return client, usdt.value

        # The branta_id can be either ciphertext. The group is returned whole.
        client, usdt_cipher = await fresh()
        usdt_scan = await service(client).verify(transfer_uri(DestinationType.UsdtEthereum, usdt_deposit, usdt_cipher))
        assert usdt_scan.status == VerifyStatus.Match
        assert [d.type for d in usdt_scan.matched_destinations] == [DestinationType.UsdtEthereum]
        assert usdt_scan.payments[0].destinations[1].is_encrypted is True

        client, usdt_cipher = await fresh()
        usdc_scan = await service(client).verify(transfer_uri(DestinationType.UsdcEthereum, usdc_deposit, usdt_cipher))
        assert usdc_scan.status == VerifyStatus.Match
        assert [d.type for d in usdc_scan.matched_destinations] == [DestinationType.UsdcEthereum]
        assert usdc_scan.payments[0].destinations[0].is_encrypted is True

        client, usdt_cipher = await fresh()
        swapped = await service(client).verify(transfer_uri(DestinationType.UsdtEthereum, SWAPPED_EVM, usdt_cipher))
        assert swapped.status == VerifyStatus.Tampered

    async def test_ethereum_usdt_scan_ignores_a_polygon_only_payment(self):
        poly = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-poly")
        client = FakeClient()
        client.payments = [Payment(destinations=[poly])]
        result = await service(client).verify(transfer_uri(DestinationType.UsdtEthereum, USDT_POLYGON, poly.value))
        assert result.status == VerifyStatus.Unknown
        assert client.payments[0].destinations[0].is_encrypted is True

    async def test_ethereum_scan_ignores_the_polygon_rail_in_the_same_payment(self):
        poly = await encrypted_secret_key_rail(USDT_POLYGON, DestinationType.UsdtPolygon, destination_id="zk-poly")
        eth_deposit = RAIL_DEPOSITS[DestinationType.UsdtEthereum]
        eth = await encrypted_secret_key_rail(eth_deposit, DestinationType.UsdtEthereum, destination_id="zk-eth")
        client = FakeClient()
        client.payments = [Payment(destinations=[poly, eth])]
        result = await service(client).verify(transfer_uri(DestinationType.UsdtEthereum, eth_deposit, eth.value))

        assert result.status == VerifyStatus.Match
        dests = result.payments[0].destinations
        assert dests[0].is_encrypted is True
        assert dests[1].is_encrypted is False
        assert len(result.matched_destinations) == 1

    @pytest.mark.parametrize(
        "function",
        ["approve", "transferFrom", "transfer;x=1"],
    )
    async def test_other_functions_are_unknown_without_get(self, function):
        rail = rail_for(DestinationType.UsdtBase)
        client = FakeClient()
        result = await service(client).verify(
            f"ethereum:{rail.contract}@{rail.chain_id}/{function}?address={SWAPPED_POLYGON}"
            f"&uint256=1&branta_id=abc&branta_secret={SECRET}"
        )
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    async def test_authority_form_is_unknown_without_get(self):
        rail = rail_for(DestinationType.UsdtBase)
        client = FakeClient()
        result = await service(client).verify(
            f"ethereum://{rail.contract}@{rail.chain_id}/transfer?address={SWAPPED_POLYGON}"
            f"&branta_id=abc&branta_secret={SECRET}"
        )
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    @pytest.mark.parametrize(
        "text",
        [
            "ethereum://[bad/transfer",
            "bitcoin://[bad",
            "ethereum:0xc2132d05d31c914a87c6611c10748aeb04b58e8f@" + "9" * 5000 + "/transfer?address=" + SWAPPED_EVM,
        ],
    )
    async def test_unparseable_input_is_unknown_and_does_not_throw(self, text):
        client = FakeClient()
        result = await service(client).verify(text)
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []

    @pytest.mark.parametrize("address", [USDT_POLYGON, USDT_TRON, USDT_TON, USDC_SOLANA])
    async def test_bare_address_is_unknown(self, address):
        client = FakeClient()
        result = await service(client).verify(address)
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []


class TestRemovedChainSchemes:
    @pytest.mark.parametrize(
        "scheme,address",
        [
            ("pol", USDT_POLYGON),
            ("eth", USDT_POLYGON),
            ("bsc", USDT_POLYGON),
            ("tron", USDT_TRON),
            ("ton", USDT_TON),
            ("sol", USDT_SOLANA),
            ("sol", USDC_SOLANA),
        ],
    )
    async def test_scheme_is_unknown_without_get_even_with_valid_params(self, scheme, address):
        dest = await encrypted_secret_key_rail(address, DestinationType.UsdtPolygon, destination_id="zk-x")
        client = FakeClient()
        client.payments = [Payment(destinations=[dest])]
        uri = (
            f"{scheme}:{address}?value=50&branta_id={quote(dest.value, safe='')}"
            f"&branta_secret={quote(SECRET, safe='')}"
        )
        result = await service(client).verify(uri)
        assert result.status == VerifyStatus.Unknown
        assert client.gets == []


POST_ONLY_RAILS = [
    (USDT_TRON, DestinationType.UsdtTron),
    (USDT_TON, DestinationType.UsdtTon),
    (USDT_SOLANA, DestinationType.UsdtSolana),
    (USDC_SOLANA, DestinationType.UsdcSolana),
]


class TestStablecoinAddPayment:
    @pytest.mark.parametrize(
        "address,destination_type",
        [(RAIL_DEPOSITS[rail.type], rail.type) for rail in EVM_TOKEN_RAILS] + POST_ONLY_RAILS,
        ids=lambda value: value.value if isinstance(value, DestinationType) else None,
    )
    async def test_add_payment_encrypts_secret_key_rail(self, address, destination_type):
        client = FakeClient()
        caller = Payment(destinations=[Destination(value=address, type=destination_type, id="zk-1")])
        result = await service(client, ["rail-secret"]).add_payment(caller)

        assert caller.destinations[0].value == address
        posted = client.posts[0].destinations[0]
        assert posted.type == destination_type
        assert posted.value != address
        assert await AesEncryption.decrypt(posted.value, "rail-secret") == address
        assert result.secret == "rail-secret"
