from __future__ import annotations

import json
import uuid
from typing import Optional

from branta.enums import DestinationType
from branta.models import Destination, Payment, Platform


class PaymentBuilder:
    def __init__(self) -> None:
        self._payment = Payment()

    def add_destination(self, address: str, type: Optional[DestinationType] = None) -> "PaymentBuilder":
        destination = Destination(value=address, id=str(uuid.uuid4()))
        if type is not None:
            destination.type = type
        self._payment.destinations.append(destination)
        return self

    def set_description(self, description: str) -> "PaymentBuilder":
        return self.add_metadata("description", description)

    def add_metadata(self, key: str, value: str) -> "PaymentBuilder":
        metadata_map: dict = json.loads(self._payment.metadata) if self._payment.metadata else {}
        metadata_map[key] = value
        self._payment.metadata = json.dumps(metadata_map)
        return self

    def set_ttl(self, ttl: int) -> "PaymentBuilder":
        self._payment.ttl = ttl
        return self

    def set_platform_logo_url(self, platform_logo_url: str) -> "PaymentBuilder":
        self._payment.platform_logo_url = platform_logo_url
        return self

    def set_child_platform(
        self,
        name: str,
        logo_url: Optional[str] = None,
        logo_light_url: Optional[str] = None,
    ) -> "PaymentBuilder":
        self._payment.child_platform = Platform(name=name, logo_url=logo_url, logo_light_url=logo_light_url)
        return self

    def build(self) -> Payment:
        return self._payment
