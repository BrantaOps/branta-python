from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import List, Optional
from urllib.parse import urlparse, quote

import aiohttp

from branta.exceptions import BrantaPaymentException
from branta.extensions import get_api_key, get_base_url, get_hmac_secret
from branta.models import Payment
from branta.options import BrantaClientOptions
from branta.v2.serialization import payment_from_api, payment_to_api

_STATUS_TEXT: dict = {
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


class BrantaClient:
    def __init__(
        self,
        default_options: Optional[BrantaClientOptions] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self._default_options = default_options
        self._session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def get_payments(
        self,
        destination_value: str,
        options: Optional[BrantaClientOptions] = None,
        signal: None = None,
    ) -> List[Payment]:
        base_url = get_base_url(self._default_options, options)
        headers = self._build_headers(options, require_api_key=False)
        encoded = quote(destination_value, safe="")
        url = f"{base_url}/v2/payments/{encoded}"

        session = await self._get_session()
        try:
            async with session.get(url, headers=headers) as response:
                if not response.ok:
                    return []
                text = await response.text()
                if not text:
                    return []
                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    return []
                payments = [payment_from_api(item) for item in parsed]
                self._verify_logo_urls(base_url, payments)
                return payments
        except BrantaPaymentException:
            raise
        except Exception:
            return []

    async def post_payment(
        self,
        payment: Payment,
        options: Optional[BrantaClientOptions] = None,
        signal: None = None,
    ) -> Optional[Payment]:
        base_url = get_base_url(self._default_options, options)
        headers = self._build_headers(options, require_api_key=True)
        headers["Content-Type"] = "application/json"
        body = json.dumps(payment_to_api(payment))

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
        options: Optional[BrantaClientOptions] = None,
        signal: None = None,
    ) -> bool:
        base_url = get_base_url(self._default_options, options)
        headers = self._build_headers(options, require_api_key=True)

        session = await self._get_session()
        try:
            async with session.get(f"{base_url}/v2/api-keys/health-check", headers=headers) as response:
                return response.ok
        except Exception:
            return False

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def _build_headers(self, options: Optional[BrantaClientOptions], require_api_key: bool) -> dict:
        headers: dict = {}
        if require_api_key:
            api_key = get_api_key(self._default_options, options)
            if api_key is None:
                raise BrantaPaymentException("Unauthorized")
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _apply_hmac_headers(
        self,
        headers: dict,
        base_url: str,
        body: str,
        options: Optional[BrantaClientOptions],
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
            base_origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        except Exception:
            return
        for payment in payments:
            logo_url = payment.platform_logo_url
            if not logo_url:
                return
            try:
                logo_origin = f"{urlparse(logo_url).scheme}://{urlparse(logo_url).netloc}"
            except Exception:
                raise BrantaPaymentException("platformLogoUrl domain does not match the configured baseUrl domain")
            if logo_origin != base_origin:
                raise BrantaPaymentException("platformLogoUrl domain does not match the configured baseUrl domain")
