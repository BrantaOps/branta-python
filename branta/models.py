from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from branta.enums import DestinationType, VerifyStatus


@dataclass
class Destination:
    value: str
    is_primary: bool = False
    is_encrypted: Optional[bool] = None
    type: Optional[DestinationType] = None
    id: Optional[str] = None
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
    brand: Optional[Platform] = None
    # Deprecated: use `brand`. Still read and written for compatibility. It is never sent on the wire.
    child_platform: Optional[Platform] = None
    is_metadata_decrypted: Optional[bool] = None


def effective_brand(payment: Payment) -> Optional[Platform]:
    """`brand` if set, otherwise the deprecated `child_platform`."""
    return payment.brand if payment.brand is not None else payment.child_platform


@dataclass
class VerifyResult:
    status: VerifyStatus
    verify_url: str
    payments: Optional[List[Payment]] = None
    # Decrypted rails that bound the scan on Match (the token is on type).
    matched_destinations: Optional[List[Destination]] = None


@dataclass
class AddPaymentResult:
    payment: Payment
    secret: str
    verify_url: str
