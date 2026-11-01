from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from branta.enums import BrantaEnvironment


@dataclass
class BrantaApiOptions:
    environment: Optional[BrantaEnvironment] = None
    api_key: Optional[str] = None
    hmac_secret: Optional[str] = None
