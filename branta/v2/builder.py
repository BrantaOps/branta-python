from __future__ import annotations

import json
import uuid
from typing import Optional

from branta.enums import DestinationType
from branta.models import Destination, Payment


class PaymentBuilder:
    def __init__(self) -> None:
        self._payment = Payment()

    def add_destination(self, address: str, type: Optional[DestinationType] = None) -> "PaymentBuilder":
        destination = Destination(value=address, is_zk=False)
        if type is not None:
            destination.type = type
        self._payment.destinations.append(destination)
        return self

    def set_zk(self) -> "PaymentBuilder":
        if self._payment.destinations:
            destination = self._payment.destinations[-1]
            destination.is_zk = True
            destination.zk_id = str(uuid.uuid4())
        return self

    def set_description(self, description: str) -> "PaymentBuilder":
        self._payment.description = description
        return self

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

    def build(self) -> Payment:
        return self._payment
