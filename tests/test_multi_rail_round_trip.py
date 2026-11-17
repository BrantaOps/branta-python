"""
Live staging add_payment → verify for every DestinationType.

Skipped unless BRANTA_RUN_INTEGRATION=1 and BRANTA_API_KEY is set.
"""
from __future__ import annotations

import os
import time
from urllib.parse import urlencode

import pytest

from branta.builder import PaymentBuilder
from branta.enums import EVM_TOKEN_RAILS, BrantaEnvironment, DestinationType, VerifyStatus
from branta.exceptions import BrantaPaymentException
from tests.live_helpers import make_service

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("BRANTA_RUN_INTEGRATION") != "1",
        reason="Live lookups skipped unless BRANTA_RUN_INTEGRATION=1",
    ),
    pytest.mark.skipif(
        not os.environ.get("BRANTA_API_KEY"),
        reason="Live POST skipped unless BRANTA_API_KEY is set",
    ),
]

TIMEOUT = 45


def _uniq() -> str:
    return f"{int(time.time() * 1000):x}{os.urandom(3).hex()}"


def bitcoin_uri(recipient: str, encrypted: str, secret: str) -> str:
    query = urlencode({"branta_id": encrypted, "branta_secret": secret})
    return f"bitcoin:{recipient}?{query}"


def transfer_uri(destination_type: DestinationType, recipient: str, encrypted: str, secret: str) -> str:
    rail = next(rail for rail in EVM_TOKEN_RAILS if rail.type == destination_type)
    query = urlencode(
        {"address": recipient, "uint256": "1000000", "branta_id": encrypted, "branta_secret": secret}
    )
    return f"ethereum:{rail.contract}@{rail.chain_id}/transfer?{query}"


def uri_without_branta(destination_type: DestinationType, recipient: str) -> str:
    if destination_type == DestinationType.BitcoinAddress:
        return f"bitcoin:{recipient}"
    rail = next(rail for rail in EVM_TOKEN_RAILS if rail.type == destination_type)
    return f"ethereum:{rail.contract}@{rail.chain_id}/transfer?address={recipient}&uint256=1000000"


def make_uri(destination_type: DestinationType, recipient: str, encrypted: str, secret: str) -> str:
    if destination_type == DestinationType.BitcoinAddress:
        return bitcoin_uri(recipient, encrypted, secret)
    return transfer_uri(destination_type, recipient, encrypted, secret)


SECRET_KEY_RAILS = [
    {
        "type": DestinationType.BitcoinAddress,
        "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
        "swapped": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "case_fold": False,
    },
    {
        "type": DestinationType.UsdtPolygon,
        "address": "0x278297528c32eCa01295B0d2135984d3442ec963",
        "swapped": "0x1111111111111111111111111111111111111111",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdcPolygon,
        "address": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
        "swapped": "0x2222222222222222222222222222222222222222",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdtEthereum,
        "address": "0xBF5550253939187432Ef4dccE8089765d3DCb47f",
        "swapped": "0x3333333333333333333333333333333333333333",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdcEthereum,
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "swapped": "0x4444444444444444444444444444444444444444",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdtBsc,
        "address": "0x55d398326f99059fF775485246999027B3197955",
        "swapped": "0x5555555555555555555555555555555555555555",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdcBsc,
        "address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "swapped": "0x6666666666666666666666666666666666666666",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdcBase,
        "address": "0x1111111111111111111111111111111111111112",
        "swapped": "0x1111111111111111111111111111111111111113",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdtBase,
        "address": "0x1111111111111111111111111111111111111114",
        "swapped": "0x1111111111111111111111111111111111111115",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdcArbitrum,
        "address": "0x1111111111111111111111111111111111111116",
        "swapped": "0x1111111111111111111111111111111111111117",
        "case_fold": True,
    },
    {
        "type": DestinationType.UsdtArbitrum,
        "address": "0x1111111111111111111111111111111111111118",
        "swapped": "0x1111111111111111111111111111111111111119",
        "case_fold": True,
    },
]

# Encrypted on add_payment, but there is no verify URI for them.
POST_ONLY_RAILS = [
    {"type": DestinationType.UsdtTron, "address": "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb", "scheme": "tron"},
    {"type": DestinationType.UsdtTon, "address": "EQDtFpEwcFAEcRe5mLVh2N6C0y-_tur3BYOM93pEZPw390by", "scheme": "ton"},
    {"type": DestinationType.UsdtSolana, "address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", "scheme": "sol"},
    {"type": DestinationType.UsdcSolana, "address": "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDofycyinf", "scheme": "sol"},
]


@pytest.mark.timeout(TIMEOUT)
@pytest.mark.parametrize("rail", SECRET_KEY_RAILS, ids=lambda r: r["type"].value)
async def test_secret_key_round_trip(rail):
    svc = make_service(BrantaEnvironment.Staging)
    added = await svc.add_payment(
        PaymentBuilder().add_destination(rail["address"], rail["type"]).set_ttl(180).build()
    )
    encrypted = added.payment.destinations[0].value
    assert added.payment.destinations[0].type == rail["type"]
    assert encrypted != rail["address"]

    match = await svc.verify(make_uri(rail["type"], rail["address"], encrypted, added.secret))
    assert match.status == VerifyStatus.Match
    assert match.matched_destinations is not None
    assert len(match.matched_destinations) == 1
    assert match.matched_destinations[0].type == rail["type"]
    if rail["case_fold"]:
        assert match.matched_destinations[0].value.lower() == rail["address"].lower()
    else:
        assert match.matched_destinations[0].value == rail["address"]

    if rail["case_fold"]:
        folded = await svc.verify(make_uri(rail["type"], rail["address"].lower(), encrypted, added.secret))
        assert folded.status == VerifyStatus.Match

    tampered = await svc.verify(make_uri(rail["type"], rail["swapped"], encrypted, added.secret))
    assert tampered.status == VerifyStatus.Tampered

    bare = await svc.verify(rail["address"])
    assert bare.status == VerifyStatus.Unknown

    no_branta = await svc.verify(uri_without_branta(rail["type"], rail["address"]))
    assert no_branta.status == VerifyStatus.Unknown


@pytest.mark.timeout(TIMEOUT)
@pytest.mark.parametrize("rail", POST_ONLY_RAILS, ids=lambda r: r["type"].value)
async def test_post_only_rail_encrypts_but_does_not_verify(rail):
    svc = make_service(BrantaEnvironment.Staging)
    added = await svc.add_payment(
        PaymentBuilder().add_destination(rail["address"], rail["type"]).set_ttl(180).build()
    )
    encrypted = added.payment.destinations[0].value
    assert added.payment.destinations[0].type == rail["type"]
    assert encrypted != rail["address"]

    query = urlencode({"branta_id": encrypted, "branta_secret": added.secret})
    result = await svc.verify(f"{rail['scheme']}:{rail['address']}?{query}")
    assert result.status == VerifyStatus.Unknown


@pytest.mark.timeout(TIMEOUT)
@pytest.mark.parametrize(
    "destination_type,factory",
    [
        (DestinationType.Bolt11, lambda: f"lnbc{_uniq()}n1ptest"),
        (DestinationType.ArkAddress, lambda: f"ark1qqroundtrip{_uniq()}"),
        (DestinationType.SilentPayment, lambda: f"sp1qqroundtrip{_uniq()}"),
    ],
    ids=["bolt11", "ark_address", "silent_payment"],
)
async def test_derived_key_round_trip(destination_type, factory):
    value = factory()
    other = factory()
    svc = make_service(BrantaEnvironment.Staging)
    added = await svc.add_payment(
        PaymentBuilder().add_destination(value, destination_type).set_ttl(180).build()
    )
    assert added.payment.destinations[0].type == destination_type
    assert added.payment.destinations[0].value != value

    match = await svc.verify(value)
    assert match.status == VerifyStatus.Match
    assert match.matched_destinations[0].type == destination_type
    assert match.matched_destinations[0].value.lower() == value.lower()

    miss = await svc.verify(other)
    assert miss.status == VerifyStatus.Unknown


@pytest.mark.timeout(TIMEOUT)
async def test_cross_chain_ethereum_usdt_does_not_bind_polygon_only_payment():
    address = "0x278297528c32eCa01295B0d2135984d3442ec963"
    svc = make_service(BrantaEnvironment.Staging)
    added = await svc.add_payment(
        PaymentBuilder().add_destination(address, DestinationType.UsdtPolygon).set_ttl(180).build()
    )
    encrypted = added.payment.destinations[0].value

    cross = await svc.verify(transfer_uri(DestinationType.UsdtEthereum, address, encrypted, added.secret))
    assert cross.status == VerifyStatus.Unknown

    correct = await svc.verify(transfer_uri(DestinationType.UsdtPolygon, address, encrypted, added.secret))
    assert correct.status == VerifyStatus.Match


@pytest.mark.timeout(TIMEOUT)
async def test_ethereum_dual_token_binds_only_the_scanned_token():
    usdt = "0xBF5550253939187432Ef4dccE8089765d3DCb47f"
    usdc = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    svc = make_service(BrantaEnvironment.Staging)
    added = await svc.add_payment(
        PaymentBuilder()
        .add_destination(usdt, DestinationType.UsdtEthereum)
        .add_destination(usdc, DestinationType.UsdcEthereum)
        .set_ttl(180)
        .build()
    )
    encrypted_usdt = added.payment.destinations[0].value

    match_usdt = await svc.verify(transfer_uri(DestinationType.UsdtEthereum, usdt, encrypted_usdt, added.secret))
    assert match_usdt.status == VerifyStatus.Match
    assert [d.type for d in match_usdt.matched_destinations] == [DestinationType.UsdtEthereum]
    usdc_dest = next(d for d in match_usdt.payments[0].destinations if d.type == DestinationType.UsdcEthereum)
    assert usdc_dest.is_encrypted is not False

    match_usdc = await svc.verify(transfer_uri(DestinationType.UsdcEthereum, usdc, encrypted_usdt, added.secret))
    assert match_usdc.status == VerifyStatus.Match
    assert [d.type for d in match_usdc.matched_destinations] == [DestinationType.UsdcEthereum]

    swapped = await svc.verify(
        transfer_uri(
            DestinationType.UsdtEthereum,
            "0x9999999999999999999999999999999999999999",
            encrypted_usdt,
            added.secret,
        )
    )
    assert swapped.status == VerifyStatus.Tampered


@pytest.mark.timeout(TIMEOUT)
async def test_reject_unknown_type_usdc_ton_at_add_payment():
    svc = make_service(BrantaEnvironment.Staging)
    payment = (
        PaymentBuilder()
        .add_destination("EQDtFpEwcFAEcRe5mLVh2N6C0y-_tur3BYOM93pEZPw390by", "usdc_ton")  # type: ignore[arg-type]
        .set_ttl(60)
        .build()
    )
    with pytest.raises(BrantaPaymentException, match="cannot be encrypted|usdc_ton"):
        await svc.add_payment(payment)
