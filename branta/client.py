from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import List, Optional
from urllib.parse import quote, urlparse

import aiohttp

from branta.exceptions import BrantaPaymentException, IncompleteError
from branta.extensions import get_api_key, get_base_url, get_hmac_secret
from branta.models import Payment
from branta.options import BrantaApiOptions
from branta.serialization import payment_from_api, payment_to_api

_STATUS_TEXT = {
    400: "BadRequest",
    401: "Unauthorized",
    403: "Forbidden",
    404: "NotFound",
    409: "Conflict",
    422: "UnprocessableEntity",
    429: "TooManyRequests",
    500: "InternalServerError",
    502: "BadGateway",
    503: "ServiceUnavailable",
    504: "GatewayTimeout",
}


def _hmac_sha256_hex(secret: str, message: str) -> str:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _encode_uri_component(value: str) -> str:
    return quote(value, safe="-_.!~*'()")


class BrantaClient:
    def __init__(
        self,
        default_options: Optional[BrantaApiOptions] = None,
        session: Optional[aiohttp.ClientSession] = None,
        *,
        integration_metrics_token: Optional[str] = None,
    ) -> None:
        self._default_options = default_options
        self._session = session
        self._integration_metrics_token = integration_metrics_token

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def get_payments(
        self,
        destination_value: str,
        options: Optional[BrantaApiOptions] = None,
    ) -> List[Payment]:
        base_url = get_base_url(self._default_options, options)
        headers = self._build_headers(options, require_api_key=False)
        url = f"{base_url}/v2/payments/{_encode_uri_component(destination_value)}"

        session = await self._get_session()
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 404:
                    return []
                if not response.ok:
                    raise IncompleteError(_STATUS_TEXT.get(response.status, str(response.status)))
                text = await response.text()
                if len(text) == 0:
                    return []
                parsed = json.loads(text)
                raw_list = parsed if isinstance(parsed, list) else []
                payments = [payment_from_api(item) for item in raw_list]
                self._verify_logo_urls(base_url, payments)
                return payments
        except (BrantaPaymentException, IncompleteError, asyncio.CancelledError):
            raise
        except Exception as exc:
            raise IncompleteError(str(exc)) from exc

    async def post_payment(
        self,
        payment: Payment,
        options: Optional[BrantaApiOptions] = None,
    ) -> Optional[Payment]:
        base_url = get_base_url(self._default_options, options)
        headers = self._build_headers(options, require_api_key=True)
        headers["Content-Type"] = "application/json"
        body = json.dumps(payment_to_api(payment), separators=(",", ":"))

        self._apply_hmac_headers(headers, base_url, body, options)

        session = await self._get_session()
        async with session.post(f"{base_url}/v2/payments", headers=headers, data=body) as response:
            if not response.ok:
                raise BrantaPaymentException(_STATUS_TEXT.get(response.status, str(response.status)))
            text = await response.text()
            if not text:
                return None
            return payment_from_api(json.loads(text))

    async def is_api_key_valid(
        self,
        options: Optional[BrantaApiOptions] = None,
    ) -> bool:
        base_url = get_base_url(self._default_options, options)
        headers = self._build_headers(options, require_api_key=True)

        session = await self._get_session()
        async with session.get(f"{base_url}/v2/api-keys/health-check", headers=headers) as response:
            return response.ok

    def _build_headers(self, options: Optional[BrantaApiOptions], require_api_key: bool) -> dict:
        headers: dict = {}
        if require_api_key:
            api_key = get_api_key(self._default_options, options)
            if api_key is None:
                raise BrantaPaymentException("Unauthorized")
            headers["Authorization"] = f"Bearer {api_key}"
        if self._integration_metrics_token:
            headers["X-Branta-Integration-Token"] = self._integration_metrics_token
        return headers

    def _apply_hmac_headers(
        self,
        headers: dict,
        base_url: str,
        body: str,
        options: Optional[BrantaApiOptions],
    ) -> None:
        hmac_secret = get_hmac_secret(self._default_options, options)
        if hmac_secret is None:
            return
        timestamp = str(int(time.time()))
        trimmed_base = base_url.rstrip("/")
        message = f"POST|{trimmed_base}/v2/payments|{body}|{timestamp}"
        signature = _hmac_sha256_hex(hmac_secret, message)
        headers["X-HMAC-Signature"] = signature
        headers["X-HMAC-Timestamp"] = timestamp

    def _verify_logo_urls(self, base_url: str, payments: List[Payment]) -> None:
        try:
            parsed = urlparse(base_url)
            base_origin = f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            return

        def check(logo_url: Optional[str], field_name: str) -> None:
            if not logo_url:
                return
            try:
                logo = urlparse(logo_url)
                logo_origin = f"{logo.scheme}://{logo.netloc}"
            except Exception as exc:
                raise BrantaPaymentException(
                    f"{field_name} domain does not match the configured API domain"
                ) from exc
            if logo_origin != base_origin:
                raise BrantaPaymentException(f"{field_name} domain does not match the configured API domain")

        for payment in payments:
            check(payment.platform_logo_url, "platform_logo_url")
            check(payment.platform_logo_light_url, "platform_logo_light_url")
            check(payment.parent_platform.logo_url if payment.parent_platform else None, "parent_platform.logo_url")
            check(
                payment.parent_platform.logo_light_url if payment.parent_platform else None,
                "parent_platform.logo_light_url",
            )
            check(payment.child_platform.logo_url if payment.child_platform else None, "child_platform.logo_url")
            check(
                payment.child_platform.logo_light_url if payment.child_platform else None,
                "child_platform.logo_light_url",
            )
