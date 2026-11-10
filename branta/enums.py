from enum import Enum
from typing import List


class BrantaEnvironment(str, Enum):
    Staging = "Staging"
    Production = "Production"
    Localhost = "Localhost"


BrantaEnvironmentUrls = {
    BrantaEnvironment.Staging: "https://staging.guardrail.branta.pro",
    BrantaEnvironment.Production: "https://guardrail.branta.pro",
    BrantaEnvironment.Localhost: "http://localhost:3000",
}


class DestinationType(str, Enum):
    BitcoinAddress = "bitcoin_address"
    Bolt11 = "bolt11"
    ArkAddress = "ark_address"
    SilentPayment = "silent_payment"
    UsdtPolygon = "usdt_polygon"
    UsdcPolygon = "usdc_polygon"


# Polygon EVM secret-key rails. A pol: URI maps to this family for verify (match-if-any).
POLYGON_EVM_DESTINATION_TYPES: List[DestinationType] = [
    DestinationType.UsdtPolygon,
    DestinationType.UsdcPolygon,
]


def is_polygon_evm_destination_type(destination_type: DestinationType) -> bool:
    return destination_type in (
        DestinationType.UsdtPolygon,
        DestinationType.UsdcPolygon,
    )


def is_secret_key_address_type(destination_type: DestinationType) -> bool:
    """Address rails encrypted with a random branta_secret (not a derived key)."""
    return destination_type == DestinationType.BitcoinAddress or is_polygon_evm_destination_type(
        destination_type
    )


class VerifyStatus(str, Enum):
    Match = "match"
    Unknown = "unknown"
    Tampered = "tampered"
    Incomplete = "incomplete"
