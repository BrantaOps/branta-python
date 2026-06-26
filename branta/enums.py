from enum import Enum


class BrantaServerBaseUrl(str, Enum):
    Staging = "https://staging.guardrail.branta.pro"
    Production = "https://guardrail.branta.pro"
    Localhost = "http://localhost:3000"


class PrivacyMode(str, Enum):
    Strict = "strict"
    Loose = "loose"


class DestinationType(str, Enum):
    BitcoinAddress = "bitcoin_address"
    Bolt11 = "bolt11"
    Bolt12 = "bolt12"
    LnUrl = "ln_url"
    TetherAddress = "tether_address"
    LnAddress = "ln_address"
    ArkAddress = "ark_address"
    SilentPayment = "silent_payment"
