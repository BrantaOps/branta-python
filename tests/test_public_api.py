"""Lock the package entry to the consumer POST/verify surface."""

import branta
from branta import DestinationType


def test_exports_consumer_surface_for_post_and_verify():
    assert branta.BrantaService is not None
    assert branta.PaymentBuilder is not None
    assert branta.DestinationType is not None
    assert branta.VerifyStatus is not None
    assert branta.BrantaEnvironment is not None
    assert branta.BrantaPaymentException is not None


def test_destination_type_includes_multi_rail_stables():
    assert DestinationType.UsdtEthereum.value == "usdt_ethereum"
    assert DestinationType.UsdcSolana.value == "usdc_solana"
    assert DestinationType.UsdtTon.value == "usdt_ton"
    assert "usdc_ton" not in {member.value for member in DestinationType}


def test_does_not_export_rail_family_internals():
    for name in (
        "POLYGON_EVM_DESTINATION_TYPES",
        "ETHEREUM_EVM_DESTINATION_TYPES",
        "BSC_EVM_DESTINATION_TYPES",
        "TRON_DESTINATION_TYPES",
        "TON_DESTINATION_TYPES",
        "SOLANA_DESTINATION_TYPES",
        "SECRET_KEY_URI_FAMILIES",
        "is_polygon_evm_destination_type",
        "is_secret_key_address_type",
    ):
        assert not hasattr(branta, name), name
