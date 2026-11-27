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
    assert DestinationType.UsdcBase.value == "usdc_base"
    assert DestinationType.UsdtArbitrum.value == "usdt_arbitrum"
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
        "EVM_TOKEN_RAILS",
        "EvmTokenRail",
        "evm_token_type",
        "is_secret_key_address_type",
    ):
        assert not hasattr(branta, name), name


def test_payment_model_has_brand_and_deprecated_child_platform():
    import dataclasses
    import warnings

    from branta import Payment, PaymentBuilder, Platform

    fields = {f.name for f in dataclasses.fields(Payment)}
    assert {"brand", "child_platform"} <= fields
    assert Payment(brand=Platform(name="Acme")).brand.name == "Acme"
    assert callable(PaymentBuilder.set_brand)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        PaymentBuilder().set_brand("Acme")
    assert callable(PaymentBuilder.set_child_platform)
