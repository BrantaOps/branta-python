from branta.enums import (
    POLYGON_EVM_DESTINATION_TYPES,
    SECRET_KEY_URI_FAMILIES,
    DestinationType,
    is_polygon_evm_destination_type,
    is_secret_key_address_type,
)


def test_destination_type_wire_format_is_exact():
    assert DestinationType.BitcoinAddress.value == "bitcoin_address"
    assert DestinationType.Bolt11.value == "bolt11"
    assert DestinationType.ArkAddress.value == "ark_address"
    assert DestinationType.SilentPayment.value == "silent_payment"
    assert DestinationType.UsdtPolygon.value == "usdt_polygon"
    assert DestinationType.UsdcPolygon.value == "usdc_polygon"


def test_polygon_evm_helpers():
    assert POLYGON_EVM_DESTINATION_TYPES == (
        DestinationType.UsdtPolygon,
        DestinationType.UsdcPolygon,
    )
    assert is_polygon_evm_destination_type(DestinationType.UsdtPolygon)
    assert is_polygon_evm_destination_type(DestinationType.UsdcPolygon)
    assert not is_polygon_evm_destination_type(DestinationType.BitcoinAddress)
    assert is_secret_key_address_type(DestinationType.BitcoinAddress)
    assert is_secret_key_address_type(DestinationType.UsdtPolygon)
    assert not is_secret_key_address_type(DestinationType.Bolt11)


def test_stablecoin_destination_type_wire_format():
    assert DestinationType.UsdtEthereum.value == "usdt_ethereum"
    assert DestinationType.UsdcEthereum.value == "usdc_ethereum"
    assert DestinationType.UsdtBsc.value == "usdt_bsc"
    assert DestinationType.UsdcBsc.value == "usdc_bsc"
    assert DestinationType.UsdtTron.value == "usdt_tron"
    assert DestinationType.UsdtTon.value == "usdt_ton"
    assert DestinationType.UsdcTon.value == "usdc_ton"
    assert DestinationType.UsdtSolana.value == "usdt_solana"
    assert DestinationType.UsdcSolana.value == "usdc_solana"


def test_secret_key_uri_families():
    assert set(SECRET_KEY_URI_FAMILIES) == {"pol", "eth", "bsc", "tron", "ton", "sol"}
    assert SECRET_KEY_URI_FAMILIES["pol"] == POLYGON_EVM_DESTINATION_TYPES
    assert SECRET_KEY_URI_FAMILIES["eth"] == (DestinationType.UsdtEthereum, DestinationType.UsdcEthereum)
    assert SECRET_KEY_URI_FAMILIES["bsc"] == (DestinationType.UsdtBsc, DestinationType.UsdcBsc)
    assert SECRET_KEY_URI_FAMILIES["tron"] == (DestinationType.UsdtTron,)
    assert SECRET_KEY_URI_FAMILIES["ton"] == (DestinationType.UsdtTon, DestinationType.UsdcTon)
    assert SECRET_KEY_URI_FAMILIES["sol"] == (DestinationType.UsdtSolana, DestinationType.UsdcSolana)


def test_is_secret_key_address_type_covers_all_stable_rails():
    assert is_secret_key_address_type(DestinationType.BitcoinAddress)
    for family in SECRET_KEY_URI_FAMILIES.values():
        for destination_type in family:
            assert is_secret_key_address_type(destination_type)
    for destination_type in (DestinationType.Bolt11, DestinationType.ArkAddress, DestinationType.SilentPayment):
        assert not is_secret_key_address_type(destination_type)
    assert not is_polygon_evm_destination_type(DestinationType.UsdtEthereum)
