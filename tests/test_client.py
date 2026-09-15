from __future__ import annotations

import json

import pytest

from branta.enums import BrantaServerBaseUrl, PrivacyMode
from branta.exceptions import BrantaPaymentException
from branta.options import BrantaClientOptions
from branta.v2.client import BrantaClient

# Matches BrantaServerBaseUrl.Localhost's value.
SAME_ORIGIN = "http://localhost:3000"
OTHER_ORIGIN = "https://attacker.example"

DESTINATIONS = [{"value": "test-destination"}]


class _FakeResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    async def text(self) -> str:
        return self._body

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def get(self, url: str, headers: dict | None = None) -> _FakeResponse:
        return self._response


def client_with_response(body: object) -> BrantaClient:
    session = _FakeSession(_FakeResponse(200, json.dumps(body)))
    options = BrantaClientOptions(base_url=BrantaServerBaseUrl.Localhost, privacy=PrivacyMode.Loose)
    return BrantaClient(default_options=options, session=session)  # type: ignore[arg-type]


async def test_checks_every_payments_logo_not_just_the_first() -> None:
    client = client_with_response(
        [
            {"destinations": DESTINATIONS},
            {"destinations": DESTINATIONS, "platform_logo_url": f"{OTHER_ORIGIN}/logo.png"},
        ]
    )

    with pytest.raises(BrantaPaymentException):
        await client.get_payments("value")


async def test_catches_mismatched_platform_logo_light_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "platform_logo_light_url": f"{OTHER_ORIGIN}/logo-light.png"}]
    )

    with pytest.raises(BrantaPaymentException, match="platform_logo_light_url"):
        await client.get_payments("value")


async def test_catches_mismatched_parent_platform_logo_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "parent_platform": {"logo_url": f"{OTHER_ORIGIN}/logo.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="parent_platform.logo_url"):
        await client.get_payments("value")


async def test_catches_mismatched_parent_platform_logo_light_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "parent_platform": {"logo_light_url": f"{OTHER_ORIGIN}/logo-light.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="parent_platform.logo_light_url"):
        await client.get_payments("value")


async def test_catches_mismatched_child_platform_logo_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "child_platform": {"logo_url": f"{OTHER_ORIGIN}/logo.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="child_platform.logo_url"):
        await client.get_payments("value")


async def test_catches_mismatched_child_platform_logo_light_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "child_platform": {"logo_light_url": f"{OTHER_ORIGIN}/logo-light.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="child_platform.logo_light_url"):
        await client.get_payments("value")


async def test_does_not_throw_when_all_logo_fields_are_same_origin_or_absent() -> None:
    client = client_with_response(
        [
            {
                "destinations": DESTINATIONS,
                "platform_logo_url": f"{SAME_ORIGIN}/a.png",
                "platform_logo_light_url": f"{SAME_ORIGIN}/b.png",
                "parent_platform": {"logo_url": f"{SAME_ORIGIN}/c.png", "logo_light_url": f"{SAME_ORIGIN}/d.png"},
                "child_platform": {"logo_url": f"{SAME_ORIGIN}/e.png"},
            },
            {"destinations": DESTINATIONS},
        ]
    )

    payments = await client.get_payments("value")

    assert len(payments) == 2
