from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


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
    UsdtSolana = "usdt_solana"
    UsdcSolana = "usdc_solana"
    UsdtBase = "usdt_base"
    UsdcBase = "usdc_base"
    UsdtArbitrum = "usdt_arbitrum"
    UsdcArbitrum = "usdc_arbitrum"


@dataclass(frozen=True)
class EvmTokenRail:
    chain_id: int
    contract: str
    type: DestinationType


# ERC-681 ethereum:<contract>@<chainId>/transfer rails.
# Chain id plus token contract select one destination type.
# Contracts are lowercase so lookup is case-insensitive.
EVM_TOKEN_RAILS: Tuple[EvmTokenRail, ...] = (
    EvmTokenRail(1, "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", DestinationType.UsdcEthereum),
    EvmTokenRail(1, "0xdac17f958d2ee523a2206206994597c13d831ec7", DestinationType.UsdtEthereum),
    EvmTokenRail(137, "0x3c499c542cef5e3811e1192ce70d8cc03d5c3359", DestinationType.UsdcPolygon),
    EvmTokenRail(137, "0xc2132d05d31c914a87c6611c10748aeb04b58e8f", DestinationType.UsdtPolygon),
    EvmTokenRail(8453, "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", DestinationType.UsdcBase),
    EvmTokenRail(8453, "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2", DestinationType.UsdtBase),
    EvmTokenRail(42161, "0xaf88d065e77c8cc2239327c5edb3a432268e5831", DestinationType.UsdcArbitrum),
    EvmTokenRail(42161, "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9", DestinationType.UsdtArbitrum),
    EvmTokenRail(56, "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d", DestinationType.UsdcBsc),
    EvmTokenRail(56, "0x55d398326f99059ff775485246999027b3197955", DestinationType.UsdtBsc),
)


def evm_token_type(chain_id: int, contract: str) -> Optional[DestinationType]:
    needle = contract.lower()
    for rail in EVM_TOKEN_RAILS:
        if rail.chain_id == chain_id and rail.contract == needle:
            return rail.type
    return None


# Address rails that add_payment encrypts with one UUID secret.
# Tron, TON, and Solana are included because add_payment still encrypts them.
# They have no verify URI.
_UUID_SECRET_DESTINATION_TYPES = frozenset(
    {
        DestinationType.BitcoinAddress,
        *(rail.type for rail in EVM_TOKEN_RAILS),
        DestinationType.UsdtTron,
        DestinationType.UsdtTon,
        DestinationType.UsdtSolana,
        DestinationType.UsdcSolana,
    }
)


def is_secret_key_address_type(destination_type: DestinationType) -> bool:
    """Address rails encrypted with a random branta_secret (not a derived key)."""
    return destination_type in _UUID_SECRET_DESTINATION_TYPES


class VerifyStatus(str, Enum):
    Match = "match"
    Unknown = "unknown"
    Tampered = "tampered"
    Incomplete = "incomplete"
