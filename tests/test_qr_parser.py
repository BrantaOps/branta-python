import pytest

from branta.enums import DestinationType
from branta.v2.parser import QRParser


class TestQRParserPlainText:
    def test_bitcoin_address_detected(self):
        parser = QRParser("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        assert parser.destination == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert parser.destination_type == DestinationType.BitcoinAddress

    def test_bech32_bitcoin_address_detected(self):
        parser = QRParser("bc1qtest")
        assert parser.destination_type == DestinationType.BitcoinAddress

    def test_bolt11_detected(self):
        parser = QRParser("lnbc100n1ptest")
        assert parser.destination_type == DestinationType.Bolt11

    def test_bolt12_detected(self):
        parser = QRParser("lnotest")
        assert parser.destination_type == DestinationType.Bolt12

    def test_lnurl_detected(self):
        parser = QRParser("LNURLtestvalue")
        assert parser.destination_type == DestinationType.LnUrl

    def test_ark_address_detected(self):
        parser = QRParser("ark1testaddress")
        assert parser.destination_type == DestinationType.ArkAddress

    def test_signet_ark_address_detected(self):
        parser = QRParser("tark1testaddress")
        assert parser.destination_type == DestinationType.ArkAddress

    def test_silent_payment_detected(self):
        parser = QRParser("sp1testpayment")
        assert parser.destination_type == DestinationType.SilentPayment

    def test_tsp1_silent_payment_detected(self):
        parser = QRParser("tsp1testpayment")
        assert parser.destination_type == DestinationType.SilentPayment

    def test_ln_address_detected(self):
        parser = QRParser("user@domain.com")
        assert parser.destination_type == DestinationType.LnAddress

    def test_ethereum_address_detected(self):
        parser = QRParser("0x" + "a" * 40)
        assert parser.destination_type == DestinationType.TetherAddress

    def test_tron_address_detected(self):
        parser = QRParser("T" + "a" * 33)
        assert parser.destination_type == DestinationType.TetherAddress

    def test_whitespace_trimmed(self):
        parser = QRParser("  bc1qtest  ")
        assert parser.destination == "bc1qtest"


class TestQRParserBitcoinURI:
    def test_bitcoin_uri_extracts_address(self):
        parser = QRParser("bitcoin:bc1qtest")
        assert parser.destination == "bc1qtest"
        assert parser.destination_type == DestinationType.BitcoinAddress

    def test_bitcoin_uri_with_query_params_extracts_address(self):
        parser = QRParser("bitcoin:bc1qtest?amount=0.001")
        assert parser.destination == "bc1qtest"

    def test_bitcoin_uri_with_lightning_param(self):
        parser = QRParser("bitcoin:bc1qtest?lightning=lnbc100n1ptest")
        assert len(parser.destinations) == 2
        assert parser.destinations[0].value == "bc1qtest"
        assert parser.destinations[1].value == "lnbc100n1ptest"
        assert parser.destinations[1].type == DestinationType.Bolt11

    def test_bitcoin_uri_with_bolt12_param(self):
        parser = QRParser("bitcoin:bc1qtest?bolt12=lnotest")
        assert parser.destinations[1].value == "lnotest"
        assert parser.destinations[1].type == DestinationType.Bolt12

    def test_bitcoin_uri_with_ark_param(self):
        parser = QRParser("bitcoin:bc1qtest?ark=ark1testaddress")
        assert parser.destinations[1].value == "ark1testaddress"
        assert parser.destinations[1].type == DestinationType.ArkAddress

    def test_bitcoin_uri_with_silent_payment_param(self):
        parser = QRParser("bitcoin:bc1qtest?silent_payment=sp1testpayment")
        assert parser.destinations[1].value == "sp1testpayment"
        assert parser.destinations[1].type == DestinationType.SilentPayment

    def test_bitcoin_uri_with_branta_params(self):
        parser = QRParser("bitcoin:bc1qtest?branta_id=enc-id&branta_secret=my-secret")
        assert parser.on_chain_encryption_text == "enc-id"
        assert parser.on_chain_encryption_secret == "my-secret"

    def test_is_on_chain_zk_true_when_both_params_present(self):
        parser = QRParser("bitcoin:bc1qtest?branta_id=enc-id&branta_secret=my-secret")
        assert parser.is_on_chain_zk() is True

    def test_is_on_chain_zk_false_when_missing_secret(self):
        parser = QRParser("bitcoin:bc1qtest?branta_id=enc-id")
        assert parser.is_on_chain_zk() is False

    def test_is_on_chain_zk_false_for_plain_address(self):
        parser = QRParser("bitcoin:bc1qtest")
        assert parser.is_on_chain_zk() is False

    def test_url_encoded_branta_params_decoded(self):
        parser = QRParser("bitcoin:bc1qtest?branta_id=enc%2Bid&branta_secret=my%20secret")
        assert parser.on_chain_encryption_text == "enc+id"
        assert parser.on_chain_encryption_secret == "my secret"


class TestQRParserLightningURI:
    def test_lightning_bolt11_uri(self):
        parser = QRParser("lightning:lnbc100n1ptest")
        assert parser.destination == "lnbc100n1ptest"
        assert parser.destination_type == DestinationType.Bolt11

    def test_lightning_uri_uppercase(self):
        parser = QRParser("LIGHTNING:LNBC100N1PTEST")
        assert parser.destination_type == DestinationType.Bolt11

    def test_lightning_bolt12_uri(self):
        parser = QRParser("lightning:lnotest")
        assert parser.destination_type == DestinationType.Bolt12


class TestQRParserEdgeCases:
    def test_unrecognized_text_sets_none_type(self):
        parser = QRParser("not-any-known-format")
        assert parser.destination == "not-any-known-format"
        assert parser.destination_type is None

    def test_uri_encoded_lightning_param_decoded(self):
        parser = QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?lightning=lnbc100n1ptest%3Dpadded")
        assert len(parser.destinations) == 2
        assert parser.destinations[1].value == "lnbc100n1ptest=padded"
        assert parser.destinations[1].type == DestinationType.Bolt11

    def test_on_chain_zk_params_url_encoded(self):
        parser = QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?branta_id=abc%2Bdef%3D&branta_secret=1234")
        assert parser.destination == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert parser.destination_type == DestinationType.BitcoinAddress
        assert parser.on_chain_encryption_text == "abc+def="
        assert parser.on_chain_encryption_secret == "1234"

    def test_combined_qr_bitcoin_and_lightning(self):
        parser = QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?&lightning=lnbc100n1ptest")
        assert len(parser.destinations) == 2
        assert parser.destination == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert parser.destination_type == DestinationType.BitcoinAddress
        assert parser.destinations[1].value == "lnbc100n1ptest"
        assert parser.destinations[1].type == DestinationType.Bolt11
        assert parser.is_on_chain_zk() is False

    def test_combined_qr_with_multiple_alts(self):
        parser = QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?&lightning=lnbc100n1ptest&ark=ark100testaddress")
        assert len(parser.destinations) == 3
        assert parser.destination == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert parser.destinations[1].value == "lnbc100n1ptest"
        assert parser.destinations[1].type == DestinationType.Bolt11
        assert parser.destinations[2].value == "ark100testaddress"
        assert parser.destinations[2].type == DestinationType.ArkAddress
        assert parser.is_on_chain_zk() is False

    def test_bitcoin_uri_with_silent_payment_param(self):
        parser = QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?silent_payment=sp1qqwl5p9jhz0000h5zkvlf9gfqv9dl9qjp5ggq5x3fw")
        assert len(parser.destinations) == 2
        assert parser.destinations[1].value == "sp1qqwl5p9jhz0000h5zkvlf9gfqv9dl9qjp5ggq5x3fw"
        assert parser.destinations[1].type == DestinationType.SilentPayment

    @pytest.mark.parametrize(
        "prefix",
        ["bitcoi\tn:", "bitcoi\nn:", "bitcoi\rn:", "\x01bitcoin:"],
    )
    def test_control_char_in_scheme_types_bitcoin_address(self, prefix):
        parser = QRParser(f"{prefix}1attackeraddr?branta_id=ID1&branta_secret=SEC1")
        assert parser.is_on_chain_zk() is True
        assert parser.destination == "1attackeraddr"
        assert parser.destination_type == DestinationType.BitcoinAddress
        assert parser.on_chain_encryption_text == "ID1"
        assert parser.on_chain_encryption_secret == "SEC1"

    def test_tab_inside_address_uses_the_address_urlparse_would_pay(self):
        parser = QRParser("bitcoin:1attac\tkeraddr?branta_id=ID1&branta_secret=SEC1")
        assert parser.destination == "1attackeraddr"
        assert parser.destination_type == DestinationType.BitcoinAddress

    def test_tab_inside_lightning_scheme_still_types_bolt11(self):
        parser = QRParser("lightnin\tg:lnbc100n1ptest")
        assert parser.destination == "lnbc100n1ptest"
        assert parser.destination_type == DestinationType.Bolt11

    def test_bip321_bc_and_tb_are_on_chain_addresses(self):
        parser = QRParser("bitcoin:?bc=bc1qmerchant&tb=tb1qtest")
        assert [d.value for d in parser.destinations] == ["bc1qmerchant", "tb1qtest"]
        assert parser.destinations[0].type == DestinationType.BitcoinAddress
        assert parser.destinations[1].type == DestinationType.BitcoinAddress
        assert parser.has_unverifiable_instruction is False

    def test_sp_param_adds_silent_payment(self):
        parser = QRParser("bitcoin:bc1qmerchant?sp=sp1qqexample")
        assert parser.destinations[1].value == "sp1qqexample"
        assert parser.destinations[1].type == DestinationType.SilentPayment
        assert parser.has_unverifiable_instruction is False

    def test_lno_and_pay_are_unverifiable(self):
        lno = QRParser("bitcoin:bc1qmerchant?lno=lno1qqexample")
        assert lno.destinations[1].value == "lno1qqexample"
        assert lno.destinations[1].type == DestinationType.Bolt12
        assert lno.has_unverifiable_instruction is True

        pay = QRParser("bitcoin:bc1qmerchant?pay=bitcoin:bc1qother")
        assert pay.has_unverifiable_instruction is True
        assert [d.value for d in pay.destinations] == ["bc1qmerchant"]

    def test_non_bitcoin_non_hash_zk_path_is_unverifiable(self):
        assert QRParser("lightning:lnotest").has_unverifiable_instruction is True
        assert QRParser("lightning:lnbc100n1ptest").has_unverifiable_instruction is False
        assert QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa").has_unverifiable_instruction is False


class TestQRParserCombined:
    def test_combined_zk_qr(self):
        qr = "bitcoin:bc1qtest?branta_id=enc-id&branta_secret=my-secret&lightning=lnbc100n1ptest&ark=ark1testaddress"
        parser = QRParser(qr)
        assert parser.is_on_chain_zk() is True
        assert len(parser.destinations) == 3
        assert parser.destinations[0].value == "bc1qtest"
        assert parser.destinations[1].value == "lnbc100n1ptest"
        assert parser.destinations[2].value == "ark1testaddress"
