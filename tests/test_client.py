from __future__ import annotations

import json

import pytest

from branta.enums import BrantaEnvironment
from branta.exceptions import BrantaPaymentException, IncompleteError
from branta.options import BrantaApiOptions
from branta.client import BrantaClient
from branta.models import Payment

# Matches BrantaEnvironment.Localhost.
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
        self.last_timeout = None
        self.last_headers: dict | None = None
        self.last_body: object = None

    def get(self, url: str, headers: dict | None = None, **kwargs: object) -> _FakeResponse:
        self.last_timeout = kwargs.get("timeout")
        self.last_headers = headers
        return self._response

    def post(self, url: str, headers: dict | None = None, data: object = None, **kwargs: object) -> _FakeResponse:
        self.last_timeout = kwargs.get("timeout")
        self.last_headers = headers
        self.last_body = data
        return self._response


def client_with_response(body: object, status: int = 200) -> BrantaClient:
    text = body if isinstance(body, str) else json.dumps(body)
    session = _FakeSession(_FakeResponse(status, text))
    options = BrantaApiOptions(environment=BrantaEnvironment.Localhost, api_key="key")
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


async def test_catches_mismatched_child_platform_alias_logo_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "child_platform": {"logo_url": f"{OTHER_ORIGIN}/logo.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="brand.logo_url"):
        await client.get_payments("value")


async def test_catches_mismatched_child_platform_alias_logo_light_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "child_platform": {"logo_light_url": f"{OTHER_ORIGIN}/logo-light.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="brand.logo_light_url"):
        await client.get_payments("value")


async def test_catches_mismatched_brand_logo_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "brand": {"logo_url": f"{OTHER_ORIGIN}/logo.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="brand.logo_url"):
        await client.get_payments("value")


async def test_catches_mismatched_brand_logo_light_url() -> None:
    client = client_with_response(
        [{"destinations": DESTINATIONS, "brand": {"logo_light_url": f"{OTHER_ORIGIN}/logo-light.png"}}]
    )

    with pytest.raises(BrantaPaymentException, match="brand.logo_light_url"):
        await client.get_payments("value")


async def test_post_payment_sends_brand_and_never_child_platform() -> None:
    from branta.models import Destination, Platform

    for payment in (
        Payment(destinations=[Destination(value="v")], brand=Platform(name="Acme", logo_url=f"{SAME_ORIGIN}/a.png")),
        Payment(destinations=[Destination(value="v")], child_platform=Platform(name="Acme", logo_url=f"{SAME_ORIGIN}/a.png")),
    ):
        client = client_with_response("")
        await client.post_payment(payment)
        body = json.loads(client._session.last_body)  # type: ignore[union-attr]
        assert body["brand"] == {"name": "Acme", "logo_url": f"{SAME_ORIGIN}/a.png"}
        assert "child_platform" not in body


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


async def test_404_returns_an_empty_list() -> None:
    client = client_with_response("", status=404)

    assert await client.get_payments("value") == []


async def test_empty_body_returns_an_empty_list() -> None:
    client = client_with_response("", status=200)

    assert await client.get_payments("value") == []


async def test_server_error_raises_incomplete() -> None:
    client = client_with_response("nope", status=500)

    with pytest.raises(IncompleteError):
        await client.get_payments("value")


async def test_get_payments_passes_30s_timeout() -> None:
    from branta.client import HTTP_TIMEOUT_SECONDS, _HTTP_TIMEOUT

    assert HTTP_TIMEOUT_SECONDS == 30
    client = client_with_response([])
    await client.get_payments("value")
    assert client._session.last_timeout is _HTTP_TIMEOUT  # type: ignore[union-attr]


async def test_get_payments_timeout_is_incomplete() -> None:
    class _TimeoutSession:
        def get(self, url: str, headers: dict | None = None, **kwargs: object) -> object:
            raise TimeoutError("timed out")

    options = BrantaApiOptions(environment=BrantaEnvironment.Localhost, api_key="key")
    client = BrantaClient(default_options=options, session=_TimeoutSession())  # type: ignore[arg-type]
    with pytest.raises(IncompleteError):
        await client.get_payments("value")


def _manifest_version() -> str:
    import re
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match is not None
    return match.group(1)


def _payment() -> Payment:
    from branta.models import Destination

    return Payment(destinations=[Destination(value="value")])


async def test_post_payment_sends_sdk_header_with_manifest_version() -> None:
    client = client_with_response("")

    await client.post_payment(_payment())

    session = client._session
    assert session.last_headers["X-Branta-SDK"] == f"python/{_manifest_version()}"  # type: ignore[union-attr]
    assert "X-Branta-SDK" not in str(session.last_body)  # type: ignore[union-attr]


async def test_post_payment_sdk_header_is_not_part_of_hmac_signature_input() -> None:
    session = _FakeSession(_FakeResponse(200, ""))
    options = BrantaApiOptions(environment=BrantaEnvironment.Localhost, api_key="key", hmac_secret="secret")
    client = BrantaClient(default_options=options, session=session)  # type: ignore[arg-type]

    await client.post_payment(_payment())

    import hashlib
    import hmac

    headers = session.last_headers or {}
    message = f"POST|{SAME_ORIGIN}/v2/payments|{session.last_body}|{headers['X-HMAC-Timestamp']}"
    expected = hmac.new(b"secret", message.encode(), hashlib.sha256).hexdigest()
    assert headers["X-HMAC-Signature"] == expected


async def test_get_payments_does_not_send_sdk_header() -> None:
    client = client_with_response([])

    await client.get_payments("value")

    assert "X-Branta-SDK" not in client._session.last_headers  # type: ignore[union-attr]


async def test_is_api_key_valid_does_not_send_sdk_header() -> None:
    client = client_with_response("")

    await client.is_api_key_valid()

    assert "X-Branta-SDK" not in client._session.last_headers  # type: ignore[union-attr]
