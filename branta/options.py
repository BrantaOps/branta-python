from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from branta.enums import BrantaServerBaseUrl, PrivacyMode


@dataclass
class BrantaClientOptions:
    base_url: BrantaServerBaseUrl
    privacy: Optional[PrivacyMode] = None
    default_api_key: Optional[str] = None
    hmac_secret: Optional[str] = None
