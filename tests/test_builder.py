import json
import warnings

import pytest

from branta.enums import DestinationType
from branta.builder import PaymentBuilder
from branta.serialization import destination_to_api


class TestPaymentBuilder:
    def test_add_destination_sets_value(self):
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        assert payment.destinations[0].value == "bc1qtest"

    def test_add_destination_assigns_id(self):
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        assert payment.destinations[0].id is not None
        assert len(payment.destinations[0].id) == 36

    def test_add_destination_with_type(self):
        payment = PaymentBuilder().add_destination("bc1qtest", DestinationType.BitcoinAddress).build()
        assert payment.destinations[0].type == DestinationType.BitcoinAddress

    def test_add_destination_assigns_unique_ids(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest1")
            .add_destination("bc1qtest2")
            .build()
        )
        assert payment.destinations[0].id != payment.destinations[1].id

    def test_set_description_writes_metadata(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_description("Test payment").build()
        assert payment.description is None
        assert json.loads(payment.metadata)["description"] == "Test payment"

    def test_set_ttl(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_ttl(3600).build()
        assert payment.ttl == 3600

    def test_set_platform_logo_url(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_platform_logo_url("https://example.com/logo.png").build()
        assert payment.platform_logo_url == "https://example.com/logo.png"

    def test_add_metadata_creates_json(self):
        payment = PaymentBuilder().add_destination("bc1qtest").add_metadata("email", "alice@example.com").build()
        parsed = json.loads(payment.metadata)
        assert parsed["email"] == "alice@example.com"

    def test_add_metadata_multiple_keys(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest")
            .add_metadata("email", "alice@example.com")
            .add_metadata("name", "Alice")
            .build()
        )
        parsed = json.loads(payment.metadata)
        assert parsed["email"] == "alice@example.com"
        assert parsed["name"] == "Alice"

    def test_multiple_destinations(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest1", DestinationType.BitcoinAddress)
            .add_destination("lnbc100n1ptest", DestinationType.Bolt11)
            .build()
        )
        assert len(payment.destinations) == 2
        assert payment.destinations[0].value == "bc1qtest1"
        assert payment.destinations[1].value == "lnbc100n1ptest"

    def test_fluent_builder_returns_self(self):
        builder = PaymentBuilder()
        result = builder.add_destination("bc1qtest")
        assert result is builder

    def test_add_destination_without_type_type_is_none(self):
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        assert payment.destinations[0].type is None

    def test_set_brand_sets_name(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_brand("Acme").build()
        assert payment.brand.name == "Acme"

    def test_set_brand_optional_urls_default_none(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_brand("Acme").build()
        assert payment.brand.logo_url is None
        assert payment.brand.logo_light_url is None

    def test_set_brand_with_urls(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest")
            .set_brand("Acme", logo_url="https://example.com/logo.png", logo_light_url="https://example.com/logo-light.png")
            .build()
        )
        assert payment.brand.logo_url == "https://example.com/logo.png"
        assert payment.brand.logo_light_url == "https://example.com/logo-light.png"

    def test_set_brand_returns_builder(self):
        builder = PaymentBuilder()
        assert builder.set_brand("Acme") is builder

    def test_set_brand_does_not_warn_or_touch_deprecated_field(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            payment = PaymentBuilder().add_destination("bc1qtest").set_brand("Acme").build()
        assert payment.child_platform is None

    def test_brand_serializes_to_api_without_child_platform(self):
        from branta.serialization import payment_to_api
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest")
            .set_brand("Acme", logo_url="https://example.com/logo.png")
            .build()
        )
        api = payment_to_api(payment)
        assert api["brand"] == {"name": "Acme", "logo_url": "https://example.com/logo.png"}
        assert "logo_light_url" not in api["brand"]
        assert "child_platform" not in api

    def test_no_brand_omitted_from_api(self):
        from branta.serialization import payment_to_api
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        api = payment_to_api(payment)
        assert "brand" not in api
        assert "child_platform" not in api

    def test_set_child_platform_is_deprecated_and_delegates_to_set_brand(self):
        from branta.serialization import payment_to_api
        expected = (
            PaymentBuilder()
            .add_destination("bc1qtest")
            .set_brand("Acme", logo_url="https://example.com/logo.png", logo_light_url="https://example.com/l.png")
            .build()
        )
        builder = PaymentBuilder().add_destination("bc1qtest")
        with pytest.warns(DeprecationWarning, match="Use set_brand / brand"):
            result = builder.set_child_platform(
                "Acme", logo_url="https://example.com/logo.png", logo_light_url="https://example.com/l.png"
            )
        assert result is builder
        payment = builder.build()
        assert payment.brand.name == "Acme"
        assert payment.child_platform is None
        # destination ids are random; compare the brand body only
        assert payment_to_api(payment)["brand"] == payment_to_api(expected)["brand"]
        assert "child_platform" not in payment_to_api(payment)

    def test_set_child_platform_warning_points_at_the_caller(self):
        with pytest.warns(DeprecationWarning) as record:
            PaymentBuilder().set_child_platform("Acme")
        assert record[0].filename == __file__

    def test_payment_with_only_deprecated_field_serializes_as_brand(self):
        from branta.models import Payment, Platform
        from branta.serialization import payment_to_api
        api = payment_to_api(Payment(child_platform=Platform(name="Old", logo_url="https://example.com/o.png")))
        assert api["brand"] == {"name": "Old", "logo_url": "https://example.com/o.png"}
        assert "child_platform" not in api

    def test_brand_wins_over_deprecated_field_when_both_set(self):
        from branta.models import Payment, Platform
        from branta.serialization import payment_to_api
        api = payment_to_api(Payment(brand=Platform(name="New"), child_platform=Platform(name="Old")))
        assert api["brand"] == {"name": "New"}
        assert "child_platform" not in api

    def test_parse_brand(self):
        from branta.serialization import payment_from_api
        payment = payment_from_api({"destinations": [], "brand": {"name": "New", "logo_url": "https://x/n.png"}})
        assert payment.brand.name == "New"
        assert payment.brand.logo_url == "https://x/n.png"
        assert payment.child_platform == payment.brand

    def test_parse_child_platform_alias(self):
        from branta.serialization import payment_from_api
        payment = payment_from_api({"destinations": [], "child_platform": {"name": "Old"}})
        assert payment.brand.name == "Old"
        assert payment.child_platform.name == "Old"

    def test_parse_both_brand_wins_and_mirrors(self):
        from branta.serialization import payment_from_api
        payment = payment_from_api(
            {"destinations": [], "brand": {"name": "New"}, "child_platform": {"name": "Old"}}
        )
        assert payment.brand.name == "New"
        assert payment.child_platform.name == "New"

    def test_parse_without_brand_leaves_both_none(self):
        from branta.serialization import payment_from_api
        payment = payment_from_api({"destinations": []})
        assert payment.brand is None
        assert payment.child_platform is None


class TestSerializationDestinationType:
    @pytest.mark.parametrize("dest_type,expected", [
        (DestinationType.BitcoinAddress, "bitcoin_address"),
        (DestinationType.Bolt11, "bolt11"),
        (DestinationType.ArkAddress, "ark_address"),
        (DestinationType.SilentPayment, "silent_payment"),
    ])
    def test_destination_type_serializes_to_correct_string(self, dest_type, expected):
        from branta.models import Destination
        destination = Destination(value="addr", type=dest_type)
        api_obj = destination_to_api(destination)
        assert api_obj["type"] == expected

    def test_destination_type_none_omitted_from_api(self):
        from branta.models import Destination
        destination = Destination(value="addr")
        api_obj = destination_to_api(destination)
        assert "type" not in api_obj

    def test_destination_always_sends_zk_true_and_id_as_zk_id(self):
        from branta.models import Destination
        destination = Destination(value="addr", id="dest-1", type=DestinationType.BitcoinAddress)
        api_obj = destination_to_api(destination)
        assert api_obj["zk"] is True
        assert api_obj["zk_id"] == "dest-1"

    def test_plaintext_description_is_not_an_api_field(self):
        from branta.models import Payment
        from branta.serialization import payment_from_api, payment_to_api

        posted = payment_to_api(Payment(description="plaintext"))
        assert "description" not in posted
        parsed = payment_from_api({"destinations": [], "description": "plaintext"})
        assert parsed.description is None
