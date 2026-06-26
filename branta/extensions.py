from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Dict, Optional

from branta.enums import DestinationType, PrivacyMode

if TYPE_CHECKING:
    from branta.options import BrantaClientOptions


def get_url(server: BrantaServerBaseUrl) -> str:
    return server.value


def get_base_url(
    default_options: Optional[BrantaClientOptions],
    override_options: Optional[BrantaClientOptions],
) -> str:
    base_url = None
    if override_options is not None and override_options.base_url is not None:
        base_url = override_options.base_url
    elif default_options is not None and default_options.base_url is not None:
        base_url = default_options.base_url
    if base_url is None:
        raise ValueError("Branta: base_url is a required option.")
    return get_url(base_url)


def get_privacy(
    default_options: Optional[BrantaClientOptions],
    override_options: Optional[BrantaClientOptions],
    fallback: PrivacyMode = PrivacyMode.Strict,
) -> PrivacyMode:
    if override_options is not None and override_options.privacy is not None:
        return override_options.privacy
    if default_options is not None and default_options.privacy is not None:
        return default_options.privacy
    return fallback


def get_api_key(
    default_options: Optional[BrantaClientOptions],
    override_options: Optional[BrantaClientOptions],
) -> Optional[str]:
    if override_options is not None and override_options.default_api_key is not None:
        return override_options.default_api_key
    if default_options is not None and default_options.default_api_key is not None:
        return default_options.default_api_key
    return None


def get_hmac_secret(
    default_options: Optional[BrantaClientOptions],
    override_options: Optional[BrantaClientOptions],
) -> Optional[str]:
    if override_options is not None and override_options.hmac_secret is not None:
        return override_options.hmac_secret
    if default_options is not None and default_options.hmac_secret is not None:
        return default_options.hmac_secret
    return None


def is_bolt11(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("lnbc") or lower.startswith("lntb") or lower.startswith("lnbcrt")


def is_ark(value: str) -> bool:
    return value.lower().startswith("ark1")


def is_silent_payment(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("sp1") or lower.startswith("tsp1")


def get_hash_zk_type(value: str) -> Optional[DestinationType]:
    if is_bolt11(value):
        return DestinationType.Bolt11
    if is_ark(value):
        return DestinationType.ArkAddress
    if is_silent_payment(value):
        return DestinationType.SilentPayment
    return None


def to_normalized_hash(value: str) -> str:
    normalized = value.lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def to_url_fragment(keys: Dict[str, str]) -> str:
    if not keys:
        return ""
    fragments = [f"k-{k}={v}" for k, v in keys.items()]
    return "#" + "&".join(fragments)
