import pytest

from branta.enums import EVM_TOKEN_RAILS, DestinationType
from branta.parser import QRParser


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

    def test_bolt12_is_not_a_destination_type(self):
        parser = QRParser("lnotest")
        assert parser.destination_type is None

    def test_lnurl_is_not_a_destination_type(self):
        parser = QRParser("LNURLtestvalue")
        assert parser.destination_type is None

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

    def test_ln_address_is_not_a_destination_type(self):
        parser = QRParser("user@domain.com")
        assert parser.destination_type is None

    def test_ethereum_address_is_not_a_destination_type(self):
        parser = QRParser("0x" + "a" * 40)
        assert parser.destination_type is None

    def test_tron_address_is_not_a_destination_type(self):
        parser = QRParser("T" + "a" * 33)
        assert parser.destination_type is None

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
        assert [d.value for d in parser.destinations] == ["bc1qtest"]
        assert parser.has_unverifiable_instruction is True

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

    def test_has_branta_params_true_when_both_params_present(self):
        parser = QRParser("bitcoin:bc1qtest?branta_id=enc-id&branta_secret=my-secret")
        assert parser.has_branta_params() is True

    def test_has_branta_params_false_when_missing_secret(self):
        parser = QRParser("bitcoin:bc1qtest?branta_id=enc-id")
        assert parser.has_branta_params() is False

    def test_has_branta_params_false_for_plain_address(self):
        parser = QRParser("bitcoin:bc1qtest")
        assert parser.has_branta_params() is False

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
        assert parser.destination_type is None
        assert parser.has_unverifiable_instruction is True


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
        assert parser.has_branta_params() is False

    def test_combined_qr_with_multiple_alts(self):
        parser = QRParser("bitcoin:1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?&lightning=lnbc100n1ptest&ark=ark100testaddress")
        assert len(parser.destinations) == 3
        assert parser.destination == "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        assert parser.destinations[1].value == "lnbc100n1ptest"
        assert parser.destinations[1].type == DestinationType.Bolt11
        assert parser.destinations[2].value == "ark100testaddress"
        assert parser.destinations[2].type == DestinationType.ArkAddress
        assert parser.has_branta_params() is False

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
        assert parser.has_branta_params() is True
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
        assert [d.value for d in parser.destinations] == ["", "bc1qmerchant", "tb1qtest"]
        assert parser.destinations[1].type == DestinationType.BitcoinAddress
        assert parser.destinations[2].type == DestinationType.BitcoinAddress
        assert parser.has_unverifiable_instruction is False

    def test_sp_param_adds_silent_payment(self):
        parser = QRParser("bitcoin:bc1qmerchant?sp=sp1qqexample")
        assert parser.destinations[1].value == "sp1qqexample"
        assert parser.destinations[1].type == DestinationType.SilentPayment
        assert parser.has_unverifiable_instruction is False

    def test_lno_and_pay_are_unverifiable(self):
        lno = QRParser("bitcoin:bc1qmerchant?lno=lno1qqexample")
        assert [d.value for d in lno.destinations] == ["bc1qmerchant"]
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
        assert parser.has_branta_params() is True
        assert len(parser.destinations) == 3
        assert parser.destinations[0].value == "bc1qtest"
        assert parser.destinations[1].value == "lnbc100n1ptest"
        assert parser.destinations[2].value == "ark1testaddress"


DEPOSIT = "0x1111111111111111111111111111111111111111"
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class TestQRParserEip681EdgeCases:
    def test_query_after_fragment_is_not_read(self):
        parser = QRParser(
            f"ethereum:{BASE_USDC}@8453/transfer#x?address={DEPOSIT}&branta_id=a&branta_secret=b"
        )
        assert parser.destination_type is None
        assert parser.on_chain_encryption_text is None
        assert parser.expected_secret_key_types == []

    def test_fragment_after_query_is_dropped(self):
        parser = QRParser(
            f"ethereum:{BASE_USDC}@8453/transfer?address={DEPOSIT}&branta_id=a&branta_secret=b#address=0x2"
        )
        assert parser.destination == DEPOSIT
        assert parser.on_chain_encryption_text == "a"

    def test_bitcoin_query_after_fragment_is_not_read(self):
        parser = QRParser("bitcoin:bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh#x?branta_id=a&branta_secret=b")
        assert parser.on_chain_encryption_text is None

    def test_digit_count_beyond_pythons_int_limit_is_untyped(self):
        parser = QRParser(f"ethereum:{BASE_USDC}@{'9' * 5000}/transfer?address={DEPOSIT}")
        assert parser.destination_type is None

    def test_leading_zero_chain_id_still_selects_the_rail(self):
        parser = QRParser(f"ethereum:{BASE_USDC}@{'0' * 4500}8453/transfer?address={DEPOSIT}")
        assert parser.destination_type == DestinationType.UsdcBase

    @pytest.mark.parametrize("text", ["ethereum://[bad/transfer", "bitcoin://[bad", "lightning://[bad"])
    def test_unparseable_authority_is_an_untyped_destination(self, text):
        parser = QRParser(text)
        assert parser.destination == text
        assert parser.destination_type is None


class TestQRParserEip681:
    def test_binds_deposit_address_and_one_token(self):
        parser = QRParser(
            f"ethereum:{BASE_USDC}@8453/transfer?address={DEPOSIT}&uint256=1000000"
            "&branta_id=abc%2Bdef%3D&branta_secret=1234"
        )
        assert parser.destination == DEPOSIT
        assert parser.destination_type == DestinationType.UsdcBase
        assert len(parser.destinations) == 1
        assert parser.destinations[0].secret_key is True
        assert parser.expected_secret_key_types == [DestinationType.UsdcBase]
        assert parser.on_chain_encryption_text == "abc+def="
        assert parser.on_chain_encryption_secret == "1234"

    def test_matches_contract_case_insensitively(self):
        address = "0x278297528c32eCa01295B0d2135984d3442ec963"
        parser = QRParser(
            f"ethereum:0xC2132D05D31C914A87C6611C10748AEB04B58E8F@137/transfer?address={address}&uint256=21"
        )
        assert parser.destination == address
        assert parser.destination_type == DestinationType.UsdtPolygon
        assert parser.expected_secret_key_types == [DestinationType.UsdtPolygon]
        assert parser.on_chain_encryption_text is None

    @pytest.mark.parametrize("rail", EVM_TOKEN_RAILS, ids=lambda rail: rail.type.value)
    def test_every_rail_binds_deposit_and_one_type(self, rail):
        parser = QRParser(
            f"ethereum:{rail.contract}@{rail.chain_id}/transfer?address={DEPOSIT}&uint256=1"
            "&branta_id=id&branta_secret=sec"
        )
        assert parser.destination == DEPOSIT
        assert parser.destination_type == rail.type
        assert parser.expected_secret_key_types == [rail.type]
        assert parser.on_chain_encryption_text == "id"
        assert parser.on_chain_encryption_secret == "sec"

    def test_uint256_is_not_part_of_the_binding(self):
        base = f"ethereum:{BASE_USDC}@8453/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234"
        a = QRParser(base + "&uint256=1")
        b = QRParser(base + "&uint256=999999999")
        assert a.destination == b.destination == DEPOSIT
        assert a.expected_secret_key_types == b.expected_secret_key_types

    def test_one_leading_slash_is_tolerated(self):
        parser = QRParser(f"ethereum:/{BASE_USDC}@8453/transfer?address={DEPOSIT}")
        assert parser.destination_type == DestinationType.UsdcBase

    def test_scheme_is_case_insensitive(self):
        parser = QRParser(f"ETHEREUM:{BASE_USDC}@8453/transfer?address={DEPOSIT}")
        assert parser.destination_type == DestinationType.UsdcBase

    def test_zero_x_upper_case_deposit_is_accepted(self):
        deposit = "0X1111111111111111111111111111111111111111"
        parser = QRParser(f"ethereum:{BASE_USDC}@8453/transfer?address={deposit}")
        assert parser.destination == deposit
        assert parser.destination_type == DestinationType.UsdcBase

    def test_first_address_param_wins(self):
        other = "0x2222222222222222222222222222222222222222"
        parser = QRParser(f"ethereum:{BASE_USDC}@8453/transfer?address={DEPOSIT}&address={other}")
        assert parser.destination == DEPOSIT

    def test_percent_encoded_ampersand_stays_inside_branta_id(self):
        other = "0x2222222222222222222222222222222222222222"
        parser = QRParser(
            f"ethereum:{BASE_USDC}@8453/transfer?address={DEPOSIT}"
            f"&branta_id=abc%26address%3D{other}&branta_secret=1234"
        )
        assert parser.destination == DEPOSIT
        assert parser.on_chain_encryption_text == f"abc&address={other}"

    def test_fragment_is_not_read_as_query(self):
        parser = QRParser(
            f"ethereum:{BASE_USDC}@8453/transfer?address={DEPOSIT}#&branta_id=abc&branta_secret=1234"
        )
        assert parser.destination_type == DestinationType.UsdcBase
        assert parser.on_chain_encryption_text is None

    @pytest.mark.parametrize(
        "uri",
        [
            # No chain id.
            f"ethereum:{BASE_USDC}/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            # Payment-request prefix and ENS-style forms.
            f"ethereum:pay-{BASE_USDC}@8453/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            f"ethereum:usdc.eth@8453/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            # // makes the contract an authority, not a path.
            f"ethereum://{BASE_USDC}@8453/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            # Only transfer is a payment. approve and transferFrom are not.
            f"ethereum:{BASE_USDC}@8453/approve?address={DEPOSIT}&uint256=1&branta_id=abc&branta_secret=1234",
            f"ethereum:{BASE_USDC}@8453/transferFrom?address={DEPOSIT}&uint256=1&branta_id=abc&branta_secret=1234",
            # Path parameters after the function name.
            f"ethereum:{BASE_USDC}@8453/transfer;x=1?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            # Chain id forms that are not plain digits.
            f"ethereum:{BASE_USDC}@0x2105/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            f"ethereum:{BASE_USDC}@8453.0/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            f"ethereum:{BASE_USDC}@8453e0/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            f"ethereum:{BASE_USDC}@-8453/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234",
            # No address, a truncated address, or an ENS recipient.
            f"ethereum:{BASE_USDC}@8453/transfer?uint256=1&branta_id=abc&branta_secret=1234",
            f"ethereum:{BASE_USDC}@8453/transfer?address=0x1111&branta_id=abc&branta_secret=1234",
            f"ethereum:{BASE_USDC}@8453/transfer?address=merchant.eth&branta_id=abc&branta_secret=1234",
        ],
    )
    def test_incomplete_forms_do_not_bind(self, uri):
        parser = QRParser(uri)
        assert parser.expected_secret_key_types == []
        assert parser.on_chain_encryption_text is None
        assert parser.on_chain_encryption_secret is None
        assert parser.destinations[0].secret_key is False
        assert parser.destinations[0].type is None

    def test_unknown_contract_does_not_bind(self):
        parser = QRParser(
            f"ethereum:0x0000000000000000000000000000000000000001@1/transfer?address={DEPOSIT}"
            "&branta_id=abc&branta_secret=1234"
        )
        assert parser.destination_type is None
        assert parser.expected_secret_key_types == []
        assert parser.on_chain_encryption_text is None

    def test_contract_on_the_wrong_chain_does_not_bind(self):
        parser = QRParser(
            f"ethereum:{BASE_USDC}@1/transfer?address={DEPOSIT}&branta_id=abc&branta_secret=1234"
        )
        assert parser.expected_secret_key_types == []
        assert parser.on_chain_encryption_text is None

    def test_bitcoin_uri_expects_bitcoin_secret_key_type(self):
        parser = QRParser("bitcoin:bc1qmerchant?branta_id=enc&branta_secret=sec")
        assert parser.destinations[0].secret_key is True
        assert parser.expected_secret_key_types == [DestinationType.BitcoinAddress]


class TestQRParserUnrecognizedScheme:
    def test_unrecognized_scheme_is_opaque_text(self):
        parser = QRParser("ethereum:0xabc?value=1")
        assert parser.destination == "ethereum:0xabc?value=1"
        assert parser.destination_type is None
        assert parser.destinations[0].secret_key is False
        assert parser.expected_secret_key_types == []
        assert parser.has_branta_params() is False


class TestQRParserRemovedChainSchemes:
    @pytest.mark.parametrize(
        "scheme,address",
        [
            ("pol", "0x278297528c32eCa01295B0d2135984d3442ec963"),
            ("eth", "0xBF5550253939187432Ef4dccE8089765d3DCb47f"),
            ("bsc", "0xBF5550253939187432Ef4dccE8089765d3DCb47f"),
            ("tron", "T9yD14Nj9j7xAB4dbGeiX9h8unkKHxuWwb"),
            ("ton", "EQDtFpEwcFAEcRe5mLVh2N6C0y-_tur3BYOM93pEZPw390by"),
            ("sol", "7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDofycyinf"),
        ],
    )
    def test_scheme_does_not_bind(self, scheme, address):
        parser = QRParser(f"{scheme}:{address}?branta_id=enc%2Bid&branta_secret=secret")
        assert parser.destination_type is None
        assert parser.expected_secret_key_types == []
        assert parser.on_chain_encryption_text is None
        assert parser.on_chain_encryption_secret is None
        assert parser.has_branta_params() is False
        assert parser.destinations[0].secret_key is False
