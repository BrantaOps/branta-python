import json

import pytest

from branta.enums import DestinationType
from branta.v2.builder import PaymentBuilder
from branta.v2.serialization import destination_to_api


class TestPaymentBuilder:
    def test_add_destination_sets_value(self):
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        assert payment.destinations[0].value == "bc1qtest"

    def test_add_destination_is_not_zk_by_default(self):
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        assert payment.destinations[0].is_zk is False

    def test_add_destination_with_type(self):
        payment = PaymentBuilder().add_destination("bc1qtest", DestinationType.BitcoinAddress).build()
        assert payment.destinations[0].type == DestinationType.BitcoinAddress

    def test_set_zk_marks_last_destination(self):
        payment = PaymentBuilder().add_destination("bc1qtest", DestinationType.BitcoinAddress).set_zk().build()
        assert payment.destinations[0].is_zk is True

    def test_set_zk_assigns_uuid(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_zk().build()
        assert payment.destinations[0].zk_id is not None
        assert len(payment.destinations[0].zk_id) == 36  # UUID format

    def test_set_zk_assigns_unique_uuids(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest1")
            .set_zk()
            .add_destination("bc1qtest2")
            .set_zk()
            .build()
        )
        assert payment.destinations[0].zk_id != payment.destinations[1].zk_id

    def test_set_description(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_description("Test payment").build()
        assert payment.description == "Test payment"

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

    def test_set_zk_only_affects_last_destination(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest1")
            .add_destination("lnbc100n1ptest")
            .set_zk()
            .build()
        )
        assert payment.destinations[0].is_zk is False
        assert payment.destinations[1].is_zk is True

    def test_fluent_builder_returns_self(self):
        builder = PaymentBuilder()
        result = builder.add_destination("bc1qtest")
        assert result is builder

    def test_set_zk_no_destinations_does_nothing(self):
        payment = PaymentBuilder().set_zk().build()
        assert len(payment.destinations) == 0

    def test_add_destination_without_type_type_is_none(self):
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        assert payment.destinations[0].type is None

    def test_set_child_platform_sets_name(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_child_platform("Acme").build()
        assert payment.child_platform.name == "Acme"

    def test_set_child_platform_optional_urls_default_none(self):
        payment = PaymentBuilder().add_destination("bc1qtest").set_child_platform("Acme").build()
        assert payment.child_platform.logo_url is None
        assert payment.child_platform.logo_light_url is None

    def test_set_child_platform_with_urls(self):
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest")
            .set_child_platform("Acme", logo_url="https://example.com/logo.png", logo_light_url="https://example.com/logo-light.png")
            .build()
        )
        assert payment.child_platform.logo_url == "https://example.com/logo.png"
        assert payment.child_platform.logo_light_url == "https://example.com/logo-light.png"

    def test_set_child_platform_returns_builder(self):
        builder = PaymentBuilder()
        result = builder.set_child_platform("Acme")
        assert result is builder

    def test_child_platform_serializes_to_api(self):
        from branta.v2.serialization import payment_to_api
        payment = (
            PaymentBuilder()
            .add_destination("bc1qtest")
            .set_child_platform("Acme", logo_url="https://example.com/logo.png")
            .build()
        )
        api = payment_to_api(payment)
        assert api["child_platform"]["name"] == "Acme"
        assert api["child_platform"]["logo_url"] == "https://example.com/logo.png"
        assert "logo_light_url" not in api["child_platform"]

    def test_no_child_platform_omitted_from_api(self):
        from branta.v2.serialization import payment_to_api
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        api = payment_to_api(payment)
        assert "child_platform" not in api


class TestSerializationDestinationType:
    @pytest.mark.parametrize("dest_type,expected", [
        (DestinationType.BitcoinAddress, "bitcoin_address"),
        (DestinationType.Bolt11, "bolt11"),
        (DestinationType.Bolt12, "bolt12"),
        (DestinationType.LnUrl, "ln_url"),
        (DestinationType.TetherAddress, "tether_address"),
        (DestinationType.LnAddress, "ln_address"),
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
