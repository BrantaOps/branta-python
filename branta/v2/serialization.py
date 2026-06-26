from __future__ import annotations

from typing import Any, Dict, Optional

from branta.enums import DestinationType
from branta.models import Destination, Payment, Platform


def destination_to_api(destination: Destination) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "value": destination.value,
        "primary": destination.is_primary,
        "zk": destination.is_zk,
    }
    if destination.type is not None:
        result["type"] = destination.type.value
    if destination.zk_id is not None:
        result["zk_id"] = destination.zk_id
    if destination.encrypted_dek is not None:
        result["encrypted_dek"] = destination.encrypted_dek
    return result


def destination_from_api(raw: Dict[str, Any]) -> Destination:
    destination = Destination(
        value=str(raw.get("value", "")),
        is_primary=bool(raw.get("primary", False)),
        is_zk=bool(raw.get("zk", False)),
    )
    raw_type = raw.get("type")
    if raw_type is not None:
        try:
            destination.type = DestinationType(raw_type)
        except ValueError:
            pass
    raw_zk_id = raw.get("zk_id")
    if raw_zk_id is not None:
        destination.zk_id = str(raw_zk_id)
    raw_encrypted_dek = raw.get("encrypted_dek")
    if raw_encrypted_dek is not None:
        destination.encrypted_dek = str(raw_encrypted_dek)
    return destination


def payment_to_api(payment: Payment) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "destinations": [destination_to_api(d) for d in payment.destinations],
    }
    if payment.description is not None:
        result["description"] = payment.description
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
    if payment.btc_pay_server_plugin_version is not None:
        result["btc_pay_server_plugin_version"] = payment.btc_pay_server_plugin_version
    return result


def payment_from_api(raw: Dict[str, Any]) -> Payment:
    destinations_raw = raw.get("destinations", [])
    if not isinstance(destinations_raw, list):
        destinations_raw = []
    payment = Payment(destinations=[destination_from_api(d) for d in destinations_raw])
    if raw.get("description") is not None:
        payment.description = str(raw["description"])
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
    if raw.get("parent_platform") is not None:
        pp = raw["parent_platform"]
        if isinstance(pp, dict):
            parent = Platform()
            if pp.get("name") is not None:
                parent.name = str(pp["name"])
            if pp.get("logo_url") is not None:
                parent.logo_url = str(pp["logo_url"])
            if pp.get("logo_light_url") is not None:
                parent.logo_light_url = str(pp["logo_light_url"])
            payment.parent_platform = parent
    if raw.get("btc_pay_server_plugin_version") is not None:
        payment.btc_pay_server_plugin_version = str(raw["btc_pay_server_plugin_version"])
    return payment
