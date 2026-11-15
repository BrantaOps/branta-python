"""
Extra live staging POST→GET combinations beyond the multi-rail round-trips.

Skipped unless BRANTA_RUN_INTEGRATION=1 and BRANTA_API_KEY is set.
"""
from __future__ import annotations

import os
from urllib.parse import quote

import pytest

from branta.enums import BrantaEnvironment, DestinationType, VerifyStatus
from branta.models import AddPaymentResult, Payment, VerifyResult
from branta.builder import PaymentBuilder
from tests.live_helpers import make_service, transfer_uri

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
    usdt_match = await must_status(transfer_uri(DestinationType.UsdtPolygon, usdt, enc_usdt, added.secret), VerifyStatus.Match)
    assert len(usdt_match.matched_destinations) == 1
    assert usdt_match.matched_destinations[0].type == DestinationType.UsdtPolygon
    usdc_match = await must_status(transfer_uri(DestinationType.UsdcPolygon, usdc, enc_usdc, added.secret), VerifyStatus.Match)
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
    # Same address under two tokens: each scan binds only the token it names.
    usdt_scan = await must_status(
        transfer_uri(DestinationType.UsdtPolygon, usdt, enc, added.secret), VerifyStatus.Match
    )
    assert [d.type for d in usdt_scan.matched_destinations] == [DestinationType.UsdtPolygon]
    usdc_scan = await must_status(
        transfer_uri(DestinationType.UsdcPolygon, usdt, enc, added.secret), VerifyStatus.Match
    )
    assert [d.type for d in usdc_scan.matched_destinations] == [DestinationType.UsdcPolygon]

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
    polygon_match = await must_status(
        transfer_uri(DestinationType.UsdtPolygon, usdt, enc_usdt, added.secret), VerifyStatus.Match
    )
    assert len(polygon_match.matched_destinations) == 1
    assert polygon_match.matched_destinations[0].type == DestinationType.UsdtPolygon
    await must_status(
        transfer_uri(DestinationType.UsdtPolygon, swap, enc_usdt, added.secret), VerifyStatus.Tampered
    )

    added = await must_add(
        PaymentBuilder().add_destination(usdt, DestinationType.UsdtPolygon).set_ttl(120).build()
    )
    enc = added.payment.destinations[0].value
    await must_status(
        transfer_uri(DestinationType.UsdtPolygon, usdt.lower(), enc, added.secret), VerifyStatus.Match
    )
    await must_status(
        transfer_uri(DestinationType.UsdtPolygon, usdt, enc, "00000000-0000-0000-0000-000000000000"),
        VerifyStatus.Unknown,
    )
    await must_status(usdt, VerifyStatus.Unknown)
    # A transfer URI with no Branta params is unknown and does not GET.
    await must_status(
        "ethereum:0xc2132d05d31c914a87c6611c10748aeb04b58e8f@137/transfer?address=" + usdt + "&uint256=50000000",
        VerifyStatus.Unknown,
    )
    # The old pol: scheme no longer verifies, even with valid params.
    await must_status(f"pol:{usdt}?branta_id={quote(enc, safe='')}&branta_secret={quote(added.secret, safe='')}", VerifyStatus.Unknown)
