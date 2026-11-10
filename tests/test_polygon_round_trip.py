"""
Live staging POST→GET for Polygon EVM rails.

Skipped unless BRANTA_RUN_INTEGRATION=1 and BRANTA_API_KEY is set.
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

import aiohttp
import pytest

from branta.enums import BrantaEnvironment, DestinationType, VerifyStatus
from branta.options import BrantaApiOptions
from branta.builder import PaymentBuilder
from branta.client import BrantaClient
from branta.service import BrantaService

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

TIMEOUT = 30


def make_service() -> BrantaService:
    options = BrantaApiOptions(
        environment=BrantaEnvironment.Staging,
        api_key=os.environ.get("BRANTA_API_KEY"),
    )
    token = os.environ.get("BRANTA_INTEGRATION_METRICS_TOKEN")
    session = aiohttp.ClientSession(headers={"X-Branta-Integration-Token": token}) if token else None
    return BrantaService(options, client=BrantaClient(options, session=session))


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
async def test_staging_usdt_polygon_round_trip():
    address = "0x278297528c32eCa01295B0d2135984d3442ec963"
    swapped = "0x1111111111111111111111111111111111111111"
    svc = make_service()
    added = await svc.add_payment(
        PaymentBuilder()
        .add_destination(address, DestinationType.UsdtPolygon)
        .set_ttl(120)
        .build()
    )
    encrypted = added.payment.destinations[0].value
    assert added.payment.destinations[0].type == DestinationType.UsdtPolygon

    match = await svc.verify(pol_uri(address, encrypted, added.secret))
    assert match.status == VerifyStatus.Match
    assert match.payments[0].destinations[0].type == DestinationType.UsdtPolygon
    assert match.payments[0].destinations[0].value.lower() == address.lower()

    lower = await svc.verify(pol_uri(address.lower(), encrypted, added.secret))
    assert lower.status == VerifyStatus.Match

    tampered = await svc.verify(pol_uri(swapped, encrypted, added.secret))
    assert tampered.status == VerifyStatus.Tampered

    bare = await svc.verify(address)
    assert bare.status == VerifyStatus.Unknown

    pol_bare = await svc.verify(f"pol:{address}?value=50&currency=USD")
    assert pol_bare.status == VerifyStatus.Unknown


@pytest.mark.timeout(TIMEOUT)
async def test_staging_usdc_polygon_round_trip():
    address = "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B"
    swapped = "0x1111111111111111111111111111111111111111"
    svc = make_service()
    added = await svc.add_payment(
        PaymentBuilder()
        .add_destination(address, DestinationType.UsdcPolygon)
        .set_ttl(120)
        .build()
    )
    encrypted = added.payment.destinations[0].value

    match = await svc.verify(pol_uri(address, encrypted, added.secret))
    assert match.status == VerifyStatus.Match
    assert match.matched_destinations[0].type == DestinationType.UsdcPolygon

    tampered = await svc.verify(pol_uri(swapped, encrypted, added.secret))
    assert tampered.status == VerifyStatus.Tampered
