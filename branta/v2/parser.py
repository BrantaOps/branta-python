from __future__ import annotations

import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from branta.enums import DestinationType
from branta.extensions import is_bolt11, is_silent_payment

_LN_ADDRESS_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ETH_HEX_RE = re.compile(r"^[0-9a-fA-F]{40}$")


def _is_ethereum_address(value: str) -> bool:
    return len(value) == 42 and value.lower().startswith("0x") and bool(_ETH_HEX_RE.match(value[2:]))


def _is_tron_address(value: str) -> bool:
    return len(value) == 34 and value.startswith("T")


def _detect_plain_text_type(value: str) -> Optional[DestinationType]:
    if is_bolt11(value):
        return DestinationType.Bolt11
    lower = value.lower()
    if lower.startswith("lno"):
        return DestinationType.Bolt12
    if lower.startswith("lnurl"):
        return DestinationType.LnUrl
    if lower.startswith("ark1"):
        return DestinationType.ArkAddress
    if is_silent_payment(value):
        return DestinationType.SilentPayment
    if _is_ethereum_address(value):
        return DestinationType.TetherAddress
    if _is_tron_address(value):
        return DestinationType.TetherAddress
    if _LN_ADDRESS_RE.match(value):
        return DestinationType.LnAddress
    if value.startswith("1") or value.startswith("3") or lower.startswith("bc1"):
        return DestinationType.BitcoinAddress
    return None


def _get_destination_type(text: str) -> Optional[DestinationType]:
    lower = text.lower()
    if lower.startswith("bitcoin:"):
        return DestinationType.BitcoinAddress
    if lower.startswith("lightning:"):
        dest = _extract_path(text)
        if dest:
            if is_bolt11(dest):
                return DestinationType.Bolt11
            if dest.lower().startswith("lno"):
                return DestinationType.Bolt12
            if dest.lower().startswith("lnurl"):
                return DestinationType.LnUrl
    return None


def _extract_path(text: str) -> Optional[str]:
    colon_idx = text.find(":")
    if colon_idx == -1:
        return None
    after_colon = text[colon_idx + 1:]
    question_idx = after_colon.find("?")
    if question_idx == -1:
        return after_colon if after_colon else None
    return after_colon[:question_idx] if after_colon[:question_idx] else None


def _parse_query_string(query: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    trimmed = query.lstrip("?")
    if not trimmed:
        return result
    for part in trimmed.split("&"):
        if not part:
            continue
        idx = part.find("=")
        if idx == -1:
            raw_key, raw_value = part, ""
        else:
            raw_key, raw_value = part[:idx], part[idx + 1:]
        if not raw_key:
            continue
        try:
            key = unquote(raw_key).lower()
            value = unquote(raw_value)
            if key not in result:
                result[key] = value
        except Exception:
            pass
    return result


class QrDestination:
    def __init__(self, value: str, type: Optional[DestinationType] = None) -> None:
        self.value = value
        self.type = type


class QRParser:
    def __init__(self, qr_text: str) -> None:
        self.destinations: List[QrDestination] = []
        self.on_chain_encryption_text: Optional[str] = None
        self.on_chain_encryption_secret: Optional[str] = None

        text = qr_text.strip()

        try:
            parsed = urlparse(text)
            scheme = parsed.scheme.lower()
        except Exception:
            self.destinations.append(QrDestination(value=text, type=_detect_plain_text_type(text)))
            return

        if not parsed.scheme:
            self.destinations.append(QrDestination(value=text, type=_detect_plain_text_type(text)))
            return

        if scheme in ("bitcoin", "lightning"):
            dest = _extract_path(text)
            if dest is not None:
                self.destinations.append(QrDestination(value=dest, type=_get_destination_type(text)))

            query = parsed.query
            params = _parse_query_string(query)

            self.on_chain_encryption_text = params.get("branta_id")
            self.on_chain_encryption_secret = params.get("branta_secret")

            lightning_value = params.get("lightning")
            if lightning_value is not None:
                self.destinations.append(QrDestination(value=lightning_value, type=_detect_plain_text_type(lightning_value)))

            bolt12_value = params.get("bolt12")
            if bolt12_value is not None:
                self.destinations.append(QrDestination(value=bolt12_value, type=_detect_plain_text_type(bolt12_value)))

            ark_value = params.get("ark")
            if ark_value is not None:
                self.destinations.append(QrDestination(value=ark_value, type=_detect_plain_text_type(ark_value)))

            silent_payment_value = params.get("silent_payment")
            if silent_payment_value is not None:
                self.destinations.append(QrDestination(value=silent_payment_value, type=_detect_plain_text_type(silent_payment_value)))

            return

        self.destinations.append(QrDestination(value=text))

    @property
    def destination(self) -> Optional[str]:
        return self.destinations[0].value if self.destinations else None

    @property
    def destination_type(self) -> Optional[DestinationType]:
        return self.destinations[0].type if self.destinations else None

    def is_on_chain_zk(self) -> bool:
        return self.on_chain_encryption_text is not None and self.on_chain_encryption_secret is not None
