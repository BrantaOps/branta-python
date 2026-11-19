from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from branta.enums import BrantaEnvironment


@dataclass
class BrantaApiOptions:
    environment: Optional[BrantaEnvironment] = None
    api_key: Optional[str] = None
    # Secret from the Secrets tab in Guardrail. Signs POST /v2/payments with X-HMAC-Signature and
    # X-HMAC-Timestamp. Needed when your platform has Require HMAC on. Server-side only.
    # See https://developer.branta.pro/setup/receive/hmac-signing
    hmac_secret: Optional[str] = None
