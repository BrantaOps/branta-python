from __future__ import annotations

import json
from typing import Any, Dict, Optional

from branta.enums import DestinationType
from branta.models import Destination, Payment, Platform

_DESTINATION_TYPES = {item.value for item in DestinationType}


def destination_to_api(destination: Destination) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "value": destination.value,
        "primary": destination.is_primary,
        "zk": True,
    }
    if destination.type is not None:
        result["type"] = destination.type.value if isinstance(destination.type, DestinationType) else destination.type
    if destination.id is not None:
        result["zk_id"] = destination.id
    if destination.encrypted_dek is not None:
        result["encrypted_dek"] = destination.encrypted_dek
    return result


def destination_from_api(raw: Dict[str, Any]) -> Destination:
    value = raw.get("value", "")
    destination = Destination(
        value="" if value is None else str(value),
        is_primary=bool(raw.get("primary", False)),
    )
    # Guardrail `zk: false` is a leftover unencrypted row — do not try to decrypt it.
    if not bool(raw.get("zk", False)):
        destination.is_encrypted = False
    raw_type = raw.get("type")
    if isinstance(raw_type, str) and raw_type in _DESTINATION_TYPES:
        destination.type = DestinationType(raw_type)
    raw_zk_id = raw.get("zk_id")
    if raw_zk_id is not None:
        destination.id = str(raw_zk_id)
    raw_encrypted_dek = raw.get("encrypted_dek")
    if raw_encrypted_dek is not None:
        destination.encrypted_dek = str(raw_encrypted_dek)
    return destination


def _platform_to_api(platform: Platform) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    if platform.name is not None:
        result["name"] = platform.name
    if platform.logo_url is not None:
        result["logo_url"] = platform.logo_url
    if platform.logo_light_url is not None:
        result["logo_light_url"] = platform.logo_light_url
    return result


def _platform_from_api(raw: Dict[str, Any]) -> Platform:
    platform = Platform()
    if raw.get("name") is not None:
        platform.name = str(raw["name"])
    if raw.get("logo_url") is not None:
        platform.logo_url = str(raw["logo_url"])
    if raw.get("logo_light_url") is not None:
        platform.logo_light_url = str(raw["logo_light_url"])
    return platform


def payment_to_api(payment: Payment) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "destinations": [destination_to_api(d) for d in payment.destinations],
    }
    if payment.created_date is not None:
        result["created_at"] = payment.created_date
    if payment.ttl is not None:
        result["ttl"] = payment.ttl
    if payment.metadata is not None:
        result["metadata"] = payment.metadata
    if payment.platform is not None:
        result["platform"] = payment.platform
    if payment.platform_logo_url is not None:
        result["platform_logo_url"] = payment.platform_logo_url
    if payment.platform_logo_light_url is not None:
        result["platform_logo_light_url"] = payment.platform_logo_light_url
    if payment.child_platform is not None:
        result["child_platform"] = _platform_to_api(payment.child_platform)
    return result


def payment_from_api(raw: Dict[str, Any]) -> Payment:
    destinations_raw = raw.get("destinations", [])
    if not isinstance(destinations_raw, list):
        destinations_raw = []
    payment = Payment(destinations=[destination_from_api(item) for item in destinations_raw])
    if raw.get("created_at") is not None:
        payment.created_date = str(raw["created_at"])
    if raw.get("ttl") is not None:
        payment.ttl = int(raw["ttl"])
    if raw.get("metadata") is not None:
        payment.metadata = str(raw["metadata"])
    if raw.get("platform") is not None:
        payment.platform = str(raw["platform"])
    if raw.get("platform_logo_url") is not None:
        payment.platform_logo_url = str(raw["platform_logo_url"])
    if raw.get("platform_logo_light_url") is not None:
        payment.platform_logo_light_url = str(raw["platform_logo_light_url"])
    parent = raw.get("parent_platform")
    if isinstance(parent, dict):
        payment.parent_platform = _platform_from_api(parent)
    child = raw.get("child_platform")
    if isinstance(child, dict):
        payment.child_platform = _platform_from_api(child)
    return payment


def _parse_metadata_map(metadata: Optional[str]) -> Dict[str, Any]:
    if metadata is None or metadata == "":
        return {}
    try:
        parsed = json.loads(metadata)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def fold_description_into_metadata(payment: Payment) -> None:
    if payment.description is None or payment.description == "":
        return
    metadata_map = _parse_metadata_map(payment.metadata)
    if "description" not in metadata_map:
        metadata_map["description"] = payment.description
    payment.metadata = json.dumps(metadata_map)
    payment.description = None


def lift_description_from_metadata(payment: Payment) -> None:
    description = _parse_metadata_map(payment.metadata).get("description")
    if isinstance(description, str):
        payment.description = description
