import json

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
        from branta.serialization import payment_to_api
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
        from branta.serialization import payment_to_api
        payment = PaymentBuilder().add_destination("bc1qtest").build()
        api = payment_to_api(payment)
        assert "child_platform" not in api


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
