from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from branta.enums import DestinationType


@dataclass
class Destination:
    value: str
    is_primary: bool = False
    is_zk: bool = False
    is_encrypted: Optional[bool] = None
    type: Optional[DestinationType] = None
    zk_id: Optional[str] = None
    encrypted_dek: Optional[str] = None


@dataclass
class Platform:
    name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_light_url: Optional[str] = None


@dataclass
class Payment:
    destinations: List[Destination] = field(default_factory=list)
    description: Optional[str] = None
    created_date: Optional[str] = None
    ttl: Optional[int] = None
    metadata: Optional[str] = None
    platform: Optional[str] = None
    platform_logo_url: Optional[str] = None
    platform_logo_light_url: Optional[str] = None
    parent_platform: Optional[Platform] = None
    btc_pay_server_plugin_version: Optional[str] = None
    is_metadata_decrypted: Optional[bool] = None

    def get_default_value(self) -> str:
        if not self.destinations:
            raise ValueError("Payment has no destinations")
        return self.destinations[0].value


@dataclass
class PaymentsResult:
    payments: List[Payment]
    verify_url: str


@dataclass
class AddPaymentResult:
    payment: Payment
    secret: str
    verify_url: str
