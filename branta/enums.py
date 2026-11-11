from enum import Enum
from typing import Dict, Tuple


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
    UsdtEthereum = "usdt_ethereum"
    UsdcEthereum = "usdc_ethereum"
    UsdtBsc = "usdt_bsc"
    UsdcBsc = "usdc_bsc"
    UsdtTron = "usdt_tron"
    UsdtTon = "usdt_ton"
    UsdcTon = "usdc_ton"
    UsdtSolana = "usdt_solana"
    UsdcSolana = "usdc_solana"


# Polygon EVM secret-key rails. A pol: URI maps to this family for verify (match-if-any).
POLYGON_EVM_DESTINATION_TYPES: Tuple[DestinationType, ...] = (
    DestinationType.UsdtPolygon,
    DestinationType.UsdcPolygon,
)


ETHEREUM_EVM_DESTINATION_TYPES: Tuple[DestinationType, ...] = (
    DestinationType.UsdtEthereum,
    DestinationType.UsdcEthereum,
)

BSC_EVM_DESTINATION_TYPES: Tuple[DestinationType, ...] = (
    DestinationType.UsdtBsc,
    DestinationType.UsdcBsc,
)

TRON_DESTINATION_TYPES: Tuple[DestinationType, ...] = (DestinationType.UsdtTron,)

TON_DESTINATION_TYPES: Tuple[DestinationType, ...] = (
    DestinationType.UsdtTon,
    DestinationType.UsdcTon,
)

SOLANA_DESTINATION_TYPES: Tuple[DestinationType, ...] = (
    DestinationType.UsdtSolana,
    DestinationType.UsdcSolana,
)

# URI scheme -> secret-key destination family for verify (match-if-any).
# Token is the destination type on the payment, not the scheme.
SECRET_KEY_URI_FAMILIES: Dict[str, Tuple[DestinationType, ...]] = {
    "pol": POLYGON_EVM_DESTINATION_TYPES,
    "eth": ETHEREUM_EVM_DESTINATION_TYPES,
    "bsc": BSC_EVM_DESTINATION_TYPES,
    "tron": TRON_DESTINATION_TYPES,
    "ton": TON_DESTINATION_TYPES,
    "sol": SOLANA_DESTINATION_TYPES,
}


def is_polygon_evm_destination_type(destination_type: DestinationType) -> bool:
    return destination_type in POLYGON_EVM_DESTINATION_TYPES


def is_secret_key_address_type(destination_type: DestinationType) -> bool:
    """Address rails encrypted with a random branta_secret (not a derived key)."""
    return destination_type == DestinationType.BitcoinAddress or any(
        destination_type in family for family in SECRET_KEY_URI_FAMILIES.values()
    )


class VerifyStatus(str, Enum):
    Match = "match"
    Unknown = "unknown"
    Tampered = "tampered"
    Incomplete = "incomplete"
