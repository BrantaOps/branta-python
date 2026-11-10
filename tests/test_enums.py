from branta.enums import (
    POLYGON_EVM_DESTINATION_TYPES,
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
