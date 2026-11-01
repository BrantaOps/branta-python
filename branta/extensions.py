from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import quote

from branta.enums import BrantaEnvironment, BrantaEnvironmentUrls, DestinationType

if TYPE_CHECKING:
    from branta.options import BrantaApiOptions


def get_url(environment: BrantaEnvironment) -> str:
    try:
        return BrantaEnvironmentUrls[environment]
    except KeyError as exc:
        raise ValueError(f"No URL defined for {environment}") from exc


def get_base_url(
    default_options: Optional["BrantaApiOptions"],
    override_options: Optional["BrantaApiOptions"],
) -> str:
    environment = None
    if override_options is not None and override_options.environment is not None:
        environment = override_options.environment
    elif default_options is not None and default_options.environment is not None:
        environment = default_options.environment
    if environment is None:
        raise ValueError("Branta: environment is a required option.")
    return get_url(environment)


def get_api_key(
    default_options: Optional["BrantaApiOptions"],
    override_options: Optional["BrantaApiOptions"],
) -> Optional[str]:
    if override_options is not None and override_options.api_key is not None:
        return override_options.api_key
    if default_options is not None and default_options.api_key is not None:
        return default_options.api_key
    return None


def get_hmac_secret(
    default_options: Optional["BrantaApiOptions"],
    override_options: Optional["BrantaApiOptions"],
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
    lower = value.lower()
    return lower.startswith("ark1") or lower.startswith("tark1")


def is_silent_payment(value: str) -> bool:
    lower = value.lower()
    return lower.startswith("sp1") or lower.startswith("tsp1")


def get_derived_key_type(value: str) -> Optional[DestinationType]:
    if is_bolt11(value):
        return DestinationType.Bolt11
    if is_ark(value):
        return DestinationType.ArkAddress
    if is_silent_payment(value):
        return DestinationType.SilentPayment
    return None


def to_normalized_hash(value: str) -> str:
    import hashlib

    normalized = value.lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


# Same reserved-character set as encodeURIComponent. UUIDs and hex hashes are unchanged.
_FRAGMENT_SAFE = "-_.!~*'()"


def _encode_fragment_component(value: str) -> str:
    return quote(value, safe=_FRAGMENT_SAFE)


def to_url_fragment(keys: Dict[str, str]) -> str:
    if not keys:
        return ""
    fragments = [
        f"k-{_encode_fragment_component(key)}={_encode_fragment_component(secret)}"
        for key, secret in keys.items()
    ]
    return "#" + "&".join(fragments)
