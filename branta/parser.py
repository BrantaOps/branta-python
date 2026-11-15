from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from branta.enums import DestinationType, evm_token_type
from branta.extensions import get_derived_key_type, is_ark, is_bolt11, is_silent_payment

_COLON_TO_QUESTION = re.compile(r"(?<=:)[^?]*")
_MALFORMED_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
_EIP681_PATH = re.compile(r"(0x[0-9a-fA-F]{40})@([0-9]+)/transfer")
_EVM_ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}", re.IGNORECASE)


@dataclass
class QrDestination:
    value: str
    type: Optional[DestinationType] = None
    # True when this address participates in the secret-key swap check.
    secret_key: bool = False


def _normalize_qr_text(qr_text: str) -> str:
    # URL parsers drop tab/LF/CR anywhere and leading/trailing C0 controls before
    # they read the scheme. Typing has to see that same text.
    value = qr_text.strip()
    start = 0
    end = len(value)
    while start < end and ord(value[start]) <= 0x20:
        start += 1
    while end > start and ord(value[end - 1]) <= 0x20:
        end -= 1
    value = value[start:end]
    return value.replace("\t", "").replace("\n", "").replace("\r", "")


def _try_parse_url(text: str):
    parsed = urlparse(text)
    if not parsed.scheme or not re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*$", parsed.scheme):
        return None
    return parsed


def _get_destination(text: str) -> Optional[str]:
    match = _COLON_TO_QUESTION.search(text)
    return match.group(0) if match else None


def _starts_with_i(value: str, prefix: str) -> bool:
    return value.lower().startswith(prefix.lower())


def detect_destination_type(value: str) -> Optional[DestinationType]:
    if is_bolt11(value):
        return DestinationType.Bolt11
    if is_ark(value):
        return DestinationType.ArkAddress
    if is_silent_payment(value):
        return DestinationType.SilentPayment
    if (
        value.startswith("1")
        or value.startswith("3")
        or _starts_with_i(value, "bc1")
        or _starts_with_i(value, "tb1")
        or _starts_with_i(value, "bcrt1")
    ):
        return DestinationType.BitcoinAddress
    return None


def _get_destination_type(text: str) -> Optional[DestinationType]:
    if _starts_with_i(text, "bitcoin:"):
        return DestinationType.BitcoinAddress
    if _starts_with_i(text, "lightning:"):
        dest = _get_destination(text)
        if dest and is_bolt11(dest):
            return DestinationType.Bolt11
    return None


def _decode_component(raw: str) -> str:
    if _MALFORMED_ESCAPE.search(raw):
        raise ValueError("malformed escape")
    return unquote(raw)


def _parse_query_string(query: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    trimmed = query[1:] if query.startswith("?") else query
    if not trimmed:
        return result
    for part in trimmed.split("&"):
        if not part:
            continue
        idx = part.find("=")
        raw_key = part if idx == -1 else part[:idx]
        raw_value = "" if idx == -1 else part[idx + 1 :]
        if not raw_key:
            continue
        try:
            key = _decode_component(raw_key).lower()
            value = _decode_component(raw_value)
        except ValueError:
            continue
        if key not in result:
            result[key] = value
    return result


def _query_from_text(text: str) -> str:
    q = text.find("?")
    if q == -1:
        return ""
    hash_idx = text.find("#", q)
    return text[q : len(text) if hash_idx == -1 else hash_idx]


def _eip681_path(text: str) -> str:
    """Path of an ethereum: URI, without scheme, query, or fragment. One leading slash is dropped."""
    rest = text[text.index(":") + 1 :]
    for delimiter in ("?", "#"):
        cut = rest.find(delimiter)
        if cut != -1:
            rest = rest[:cut]
    return rest[1:] if rest.startswith("/") else rest


def _parse_eip681(text: str) -> Optional[Tuple[DestinationType, str]]:
    """ERC-681 token transfer. Chain id and contract select one destination type.
    The deposit address is the `address` query param."""
    match = _EIP681_PATH.fullmatch(_eip681_path(text))
    if match is None:
        return None
    destination_type = evm_token_type(int(match.group(2)), match.group(1))
    if destination_type is None:
        return None
    address = _parse_query_string(_query_from_text(text)).get("address")
    if address is None or _EVM_ADDRESS.fullmatch(address) is None:
        return None
    return destination_type, address


class QRParser:
    def __init__(self, qr_text: str) -> None:
        self.destinations: list[QrDestination] = []
        # branta_id / branta_secret from a bitcoin: or ERC-681 ethereum: URI (legacy "on_chain" names).
        self.on_chain_encryption_text: Optional[str] = None
        self.on_chain_encryption_secret: Optional[str] = None
        self.has_unverifiable_instruction = False
        # Destination types this scan may decrypt.
        # ERC-681 sets one type from the chain id and token contract. Bitcoin sets bitcoin_address.
        # Empty when the QR has no secret-key instruction.
        self.expected_secret_key_types: List[DestinationType] = []

        text = _normalize_qr_text(qr_text)
        uri = _try_parse_url(text)
        if uri is None:
            self.destinations.append(QrDestination(value=text, type=detect_destination_type(text)))
            return

        scheme = uri.scheme.lower()
        if scheme == "ethereum":
            transfer = _parse_eip681(text)
            if transfer is None:
                self.destinations.append(QrDestination(value=text))
                return
            destination_type, address = transfer
            self.destinations.append(QrDestination(value=address, type=destination_type, secret_key=True))
            self.expected_secret_key_types = [destination_type]
            query_params = _parse_query_string(_query_from_text(text))
            if "branta_id" in query_params:
                self.on_chain_encryption_text = query_params["branta_id"]
            if "branta_secret" in query_params:
                self.on_chain_encryption_secret = query_params["branta_secret"]
            return

        if scheme in ("bitcoin", "lightning"):
            dest = _get_destination(text)
            if dest is not None:
                dest_type = _get_destination_type(text)
                self.destinations.append(
                    QrDestination(
                        value=dest,
                        type=dest_type,
                        secret_key=dest_type == DestinationType.BitcoinAddress,
                    )
                )
                if dest != "" and dest_type != DestinationType.BitcoinAddress and get_derived_key_type(dest) is None:
                    self.has_unverifiable_instruction = True

            query_params = _parse_query_string(_query_from_text(text))

            if "branta_id" in query_params:
                self.on_chain_encryption_text = query_params["branta_id"]
            if "branta_secret" in query_params:
                self.on_chain_encryption_secret = query_params["branta_secret"]

            def add_bindable(key: str, on_chain: bool) -> None:
                if key not in query_params:
                    return
                value = query_params[key]
                dest_type = DestinationType.BitcoinAddress if on_chain else detect_destination_type(value)
                if value != "" and not on_chain and get_derived_key_type(value) is None:
                    self.has_unverifiable_instruction = True
                    return
                self.destinations.append(QrDestination(value=value, type=dest_type, secret_key=on_chain))

            add_bindable("lightning", False)
            add_bindable("ark", False)
            add_bindable("silent_payment", False)
            add_bindable("bc", True)
            add_bindable("tb", True)
            add_bindable("sp", False)
            if "bolt12" in query_params:
                self.has_unverifiable_instruction = True
            if "lno" in query_params:
                self.has_unverifiable_instruction = True
            if "pay" in query_params:
                self.has_unverifiable_instruction = True

            if any(d.secret_key for d in self.destinations):
                self.expected_secret_key_types = [DestinationType.BitcoinAddress]
            return

        self.destinations.append(QrDestination(value=text))

    @property
    def destination(self) -> Optional[str]:
        return self.destinations[0].value if self.destinations else None

    @property
    def destination_type(self) -> Optional[DestinationType]:
        return self.destinations[0].type if self.destinations else None

    def has_branta_params(self) -> bool:
        return self.on_chain_encryption_text is not None and self.on_chain_encryption_secret is not None
