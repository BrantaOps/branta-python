from branta.enums import (
    EVM_TOKEN_RAILS,
    DestinationType,
    evm_token_type,
    is_secret_key_address_type,
)


def test_destination_type_wire_format_is_exact():
    assert DestinationType.BitcoinAddress.value == "bitcoin_address"
    assert DestinationType.Bolt11.value == "bolt11"
    assert DestinationType.ArkAddress.value == "ark_address"
    assert DestinationType.SilentPayment.value == "silent_payment"
    assert DestinationType.UsdtPolygon.value == "usdt_polygon"
    assert DestinationType.UsdcPolygon.value == "usdc_polygon"


def test_stablecoin_destination_type_wire_format():
    assert DestinationType.UsdtEthereum.value == "usdt_ethereum"
    assert DestinationType.UsdcEthereum.value == "usdc_ethereum"
    assert DestinationType.UsdtBsc.value == "usdt_bsc"
    assert DestinationType.UsdcBsc.value == "usdc_bsc"
    assert DestinationType.UsdtTron.value == "usdt_tron"
    assert DestinationType.UsdtTon.value == "usdt_ton"
    assert DestinationType.UsdtSolana.value == "usdt_solana"
    assert DestinationType.UsdcSolana.value == "usdc_solana"
    assert DestinationType.UsdtBase.value == "usdt_base"
    assert DestinationType.UsdcBase.value == "usdc_base"
    assert DestinationType.UsdtArbitrum.value == "usdt_arbitrum"
    assert DestinationType.UsdcArbitrum.value == "usdc_arbitrum"
    # usdc_ton deferred until a platform names a concrete TON USDC jetton.
    assert "usdc_ton" not in {member.value for member in DestinationType}


def test_evm_token_rails_cover_five_networks_with_one_type_each():
    assert {rail.chain_id for rail in EVM_TOKEN_RAILS} == {1, 137, 56, 8453, 42161}
    assert len(EVM_TOKEN_RAILS) == 10
    assert len({rail.type for rail in EVM_TOKEN_RAILS}) == 10
    assert len({(rail.chain_id, rail.contract) for rail in EVM_TOKEN_RAILS}) == 10
    for rail in EVM_TOKEN_RAILS:
        assert rail.contract == rail.contract.lower()


def test_evm_token_type_selects_by_chain_id_and_contract():
    assert evm_token_type(1, "0xdAC17F958D2ee523a2206206994597C13D831ec7") == DestinationType.UsdtEthereum
    assert evm_token_type(1, "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48") == DestinationType.UsdcEthereum
    assert evm_token_type(137, "0xc2132D05D31c914a87C6611C10748AEb04B58e8F") == DestinationType.UsdtPolygon
    assert evm_token_type(137, "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359") == DestinationType.UsdcPolygon
    assert evm_token_type(56, "0x55d398326f99059fF775485246999027B3197955") == DestinationType.UsdtBsc
    assert evm_token_type(56, "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d") == DestinationType.UsdcBsc
    assert evm_token_type(8453, "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2") == DestinationType.UsdtBase
    assert evm_token_type(8453, "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913") == DestinationType.UsdcBase
    assert evm_token_type(42161, "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9") == DestinationType.UsdtArbitrum
    assert evm_token_type(42161, "0xaf88d065e77c8cC2239327C5EDb3A432268e5831") == DestinationType.UsdcArbitrum


def test_evm_token_type_misses_on_wrong_chain_or_unknown_contract():
    # Same contract on the wrong chain is not a rail.
    assert evm_token_type(8453, "0xdAC17F958D2ee523a2206206994597C13D831ec7") is None
    # Polygon bridged USDC.e is not the native USDC contract.
    assert evm_token_type(137, "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174") is None
    # Arbitrum Nova is not Arbitrum One.
    assert evm_token_type(42170, "0xaf88d065e77c8cC2239327C5EDb3A432268e5831") is None


def test_is_secret_key_address_type_covers_bitcoin_evm_rails_and_post_only_types():
    assert is_secret_key_address_type(DestinationType.BitcoinAddress)
    for rail in EVM_TOKEN_RAILS:
        assert is_secret_key_address_type(rail.type)
    # Tron, TON, and Solana still encrypt on add_payment. They have no verify URI.
    for destination_type in (
        DestinationType.UsdtTron,
        DestinationType.UsdtTon,
        DestinationType.UsdtSolana,
        DestinationType.UsdcSolana,
    ):
        assert is_secret_key_address_type(destination_type)
    for destination_type in (DestinationType.Bolt11, DestinationType.ArkAddress, DestinationType.SilentPayment):
        assert not is_secret_key_address_type(destination_type)
