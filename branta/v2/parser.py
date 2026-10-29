from __future__ import annotations

import re
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from branta.enums import DestinationType
from branta.extensions import get_hash_zk_type, is_ark, is_bolt11, is_silent_payment

_LN_ADDRESS_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ETH_HEX_RE = re.compile(r"^[0-9a-fA-F]{40}$")
# urllib.parse.urlparse strips these before it reads the scheme: leading C0 controls
# and spaces, then tab/LF/CR anywhere. It does not strip trailing C0 controls.
_URLPARSE_LEADING_C0_OR_SPACE = "".join(chr(code) for code in range(0x21))


def _normalize_qr_text(qr_text: str) -> str:
    # Destination typing reads the raw text. It has to see the same string urlparse
    # does, or a control byte inside "bitcoin:" leaves the address untyped and the
    # swap check never runs.
    value = qr_text.strip()
    value = value.lstrip(_URLPARSE_LEADING_C0_OR_SPACE)
    for char in ("\t", "\n", "\r"):
        value = value.replace(char, "")
    return value


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
    if is_ark(value):
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
        # A payable instruction this SDK cannot bind to a decrypted destination.
        self.has_unverifiable_instruction = False

        text = _normalize_qr_text(qr_text)

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
                dest_type = _get_destination_type(text)
                self.destinations.append(QrDestination(value=dest, type=dest_type))
                if (
                    dest != ""
                    and dest_type != DestinationType.BitcoinAddress
                    and get_hash_zk_type(dest) is None
                ):
                    self.has_unverifiable_instruction = True

            query = parsed.query
            params = _parse_query_string(query)

            self.on_chain_encryption_text = params.get("branta_id")
            self.on_chain_encryption_secret = params.get("branta_secret")

            def add_bindable(value: Optional[str], type: Optional[DestinationType], on_chain: bool) -> None:
                if value is None:
                    return
                self.destinations.append(QrDestination(value=value, type=type))
                if value != "" and not on_chain and get_hash_zk_type(value) is None:
                    self.has_unverifiable_instruction = True

            for key in ("lightning", "bolt12", "ark", "silent_payment"):
                value = params.get(key)
                add_bindable(value, _detect_plain_text_type(value or ""), False)
            for key in ("bc", "tb"):
                add_bindable(params.get(key), DestinationType.BitcoinAddress, True)
            sp_value = params.get("sp")
            add_bindable(sp_value, _detect_plain_text_type(sp_value or ""), False)
            lno_value = params.get("lno")
            lno_type = (_detect_plain_text_type(lno_value) or DestinationType.Bolt12) if lno_value else None
            add_bindable(lno_value, lno_type, False)
            if params.get("pay"):
                self.has_unverifiable_instruction = True

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
