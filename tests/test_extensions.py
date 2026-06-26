import pytest

from branta.enums import BrantaServerBaseUrl, DestinationType
from branta.extensions import (
    get_hash_zk_type,
    get_url,
    is_ark,
    is_bolt11,
    is_silent_payment,
    to_normalized_hash,
    to_url_fragment,
)


class TestGetUrl:
    def test_localhost(self):
        assert get_url(BrantaServerBaseUrl.Localhost) == "http://localhost:3000"

    def test_production(self):
        assert get_url(BrantaServerBaseUrl.Production) == "https://guardrail.branta.pro"

    def test_staging(self):
        assert get_url(BrantaServerBaseUrl.Staging) == "https://staging.guardrail.branta.pro"


class TestIsBolt11:
    def test_lnbc_is_bolt11(self):
        assert is_bolt11("lnbc100n1ptest") is True

    def test_lntb_is_bolt11(self):
        assert is_bolt11("lntb100n1ptest") is True

    def test_lnbcrt_is_bolt11(self):
        assert is_bolt11("lnbcrt100n1ptest") is True

    def test_uppercase_is_bolt11(self):
        assert is_bolt11("LNBC100N1PTEST") is True

    def test_mixed_case_is_bolt11(self):
        assert is_bolt11("LnBc100n1ptest") is True

    def test_bitcoin_address_not_bolt11(self):
        assert is_bolt11("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") is False

    def test_empty_string_not_bolt11(self):
        assert is_bolt11("") is False


class TestIsArk:
    def test_ark1_prefix_is_ark(self):
        assert is_ark("ark1testaddress") is True

    def test_uppercase_is_ark(self):
        assert is_ark("ARK1TESTADDRESS") is True

    def test_bitcoin_address_not_ark(self):
        assert is_ark("bc1qtest") is False


class TestIsSilentPayment:
    def test_sp1_is_silent_payment(self):
        assert is_silent_payment("sp1testpayment") is True

    def test_tsp1_is_silent_payment(self):
        assert is_silent_payment("tsp1testpayment") is True

    def test_uppercase_is_silent_payment(self):
        assert is_silent_payment("SP1TESTPAYMENT") is True

    def test_bitcoin_address_not_silent_payment(self):
        assert is_silent_payment("bc1qtest") is False


class TestGetHashZkType:
    def test_bolt11_returns_bolt11_type(self):
        assert get_hash_zk_type("lnbc100n1ptest") == DestinationType.Bolt11

    def test_ark_returns_ark_type(self):
        assert get_hash_zk_type("ark1testaddress") == DestinationType.ArkAddress

    def test_silent_payment_returns_silent_payment_type(self):
        assert get_hash_zk_type("sp1testpayment") == DestinationType.SilentPayment

    def test_bitcoin_address_returns_none(self):
        assert get_hash_zk_type("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") is None

    def test_random_string_returns_none(self):
        assert get_hash_zk_type("random-string") is None


class TestToNormalizedHash:
    def test_produces_uppercase_hex(self):
        result = to_normalized_hash("lnbc100n1ptest")
        assert result == result.upper()
        assert all(c in "0123456789ABCDEF" for c in result)

    def test_lowercase_input_same_as_uppercase(self):
        assert to_normalized_hash("LNBC100N1PTEST") == to_normalized_hash("lnbc100n1ptest")

    def test_produces_64_char_sha256(self):
        result = to_normalized_hash("test-value")
        assert len(result) == 64

    def test_known_value(self):
        import hashlib
        value = "lnbc100n1ptest"
        expected = hashlib.sha256(value.lower().encode()).hexdigest().upper()
        assert to_normalized_hash(value) == expected


class TestToUrlFragment:
    def test_empty_dict_returns_empty_string(self):
        assert to_url_fragment({}) == ""

    def test_single_key_formats_correctly(self):
        result = to_url_fragment({"abc-123": "my-secret"})
        assert result == "#k-abc-123=my-secret"

    def test_multiple_keys_joined_with_ampersand(self):
        result = to_url_fragment({"id1": "key1", "id2": "key2"})
        assert result == "#k-id1=key1&k-id2=key2"
