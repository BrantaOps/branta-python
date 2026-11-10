"""
Extra live staging POST→GET combinations beyond the dedicated polygon round-trips.

Skipped unless BRANTA_RUN_INTEGRATION=1 and BRANTA_API_KEY is set.
"""
from __future__ import annotations

import os
from urllib.parse import quote, urlencode

import pytest

from branta.enums import BrantaEnvironment, DestinationType, VerifyStatus
from branta.models import AddPaymentResult, Payment, VerifyResult
from branta.builder import PaymentBuilder
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

TIMEOUT = 60


def pol_uri(recipient: str, encrypted: str, secret: str) -> str:
    query = urlencode(
        {
            "value": "50",
            "user": "send",
            "currency": "USD",
            "branta_id": encrypted,
            "branta_secret": secret,
        }
    )
    return f"pol:{recipient}?{query}"


@pytest.mark.timeout(TIMEOUT)
async def test_staging_live_combos():
    svc = make_service(BrantaEnvironment.Staging)
    btc = "bc1qgw3dzmhnyvcswc9r0v0z0ajtp8ulm4nuyeahwr"
    usdt = "0x278297528c32eCa01295B0d2135984d3442ec963"
    usdc = "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"
    swap = "0x1111111111111111111111111111111111111111"
    btc_sw = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

    async def must_add(payment: Payment) -> AddPaymentResult:
        return await svc.add_payment(payment)

    async def must_status(qr: str, want: VerifyStatus) -> VerifyResult:
        result = await svc.verify(qr)
        assert result.status == want, qr
        return result

    added = await must_add(
        PaymentBuilder().add_destination(btc, DestinationType.BitcoinAddress).set_ttl(120).build()
    )
    enc = added.payment.destinations[0].value
    qr = f"bitcoin:{btc}?branta_id={quote(enc, safe='')}&branta_secret={quote(added.secret, safe='')}"
    match = await must_status(qr, VerifyStatus.Match)
    assert len(match.matched_destinations) == 1
    assert match.matched_destinations[0].type == DestinationType.BitcoinAddress
    await must_status(
        f"bitcoin:{btc_sw}?branta_id={quote(enc, safe='')}&branta_secret={quote(added.secret, safe='')}",
        VerifyStatus.Tampered,
    )
    await must_status(f"bitcoin:{btc}", VerifyStatus.Unknown)

    added = await must_add(
        PaymentBuilder()
        .add_destination(usdt, DestinationType.UsdtPolygon)
        .add_destination(usdc, DestinationType.UsdcPolygon)
        .set_ttl(120)
        .build()
    )
    enc_usdt = ""
    enc_usdc = ""
    for d in added.payment.destinations:
        if d.type == DestinationType.UsdtPolygon:
            enc_usdt = d.value
        elif d.type == DestinationType.UsdcPolygon:
            enc_usdc = d.value
    usdt_match = await must_status(pol_uri(usdt, enc_usdt, added.secret), VerifyStatus.Match)
    assert len(usdt_match.matched_destinations) == 1
    assert usdt_match.matched_destinations[0].type == DestinationType.UsdtPolygon
    usdc_match = await must_status(pol_uri(usdc, enc_usdc, added.secret), VerifyStatus.Match)
    assert len(usdc_match.matched_destinations) == 1
    assert usdc_match.matched_destinations[0].type == DestinationType.UsdcPolygon

    added = await must_add(
        PaymentBuilder()
        .add_destination(usdt, DestinationType.UsdtPolygon)
        .add_destination(usdt, DestinationType.UsdcPolygon)
        .set_ttl(120)
        .build()
    )
    enc = added.payment.destinations[0].value
    both = await must_status(pol_uri(usdt, enc, added.secret), VerifyStatus.Match)
    assert len(both.matched_destinations) == 2

    added = await must_add(
        PaymentBuilder()
        .add_destination(btc, DestinationType.BitcoinAddress)
        .add_destination(usdt, DestinationType.UsdtPolygon)
        .set_ttl(120)
        .build()
    )
    enc_btc = ""
    enc_usdt = ""
    for d in added.payment.destinations:
        if d.type == DestinationType.BitcoinAddress:
            enc_btc = d.value
        elif d.type == DestinationType.UsdtPolygon:
            enc_usdt = d.value
    btc_match = await must_status(
        f"bitcoin:{btc}?branta_id={quote(enc_btc, safe='')}&branta_secret={quote(added.secret, safe='')}",
        VerifyStatus.Match,
    )
    assert len(btc_match.matched_destinations) == 1
    assert btc_match.matched_destinations[0].type == DestinationType.BitcoinAddress
    pol_match = await must_status(pol_uri(usdt, enc_usdt, added.secret), VerifyStatus.Match)
    assert len(pol_match.matched_destinations) == 1
    assert pol_match.matched_destinations[0].type == DestinationType.UsdtPolygon
    await must_status(pol_uri(swap, enc_usdt, added.secret), VerifyStatus.Tampered)

    added = await must_add(
        PaymentBuilder().add_destination(usdt, DestinationType.UsdtPolygon).set_ttl(120).build()
    )
    enc = added.payment.destinations[0].value
    await must_status(pol_uri(usdt.lower(), enc, added.secret), VerifyStatus.Match)
    await must_status(pol_uri(usdt, enc, "00000000-0000-0000-0000-000000000000"), VerifyStatus.Unknown)
    await must_status(usdt, VerifyStatus.Unknown)
    await must_status(f"pol:{usdt}?value=50&currency=USD", VerifyStatus.Unknown)
