"""
Integration tests against live Branta endpoints.

Skipped unless BRANTA_RUN_INTEGRATION=1 — local `pytest` and PR CI must not hit Guardrail.
Run with: BRANTA_RUN_INTEGRATION=1 pytest tests/test_integration.py -v

Fixtures are the published example QR codes. See the developer docs.
"""
from __future__ import annotations

import os

import aiohttp
import pytest

from branta.enums import BrantaEnvironment, VerifyStatus
from branta.options import BrantaApiOptions
from branta.client import BrantaClient
from branta.service import BrantaService

pytestmark = pytest.mark.skipif(
    os.environ.get("BRANTA_RUN_INTEGRATION") != "1",
    reason="Live lookups skipped unless BRANTA_RUN_INTEGRATION=1",
)

TIMEOUT = 15


def make_service(environment: BrantaEnvironment) -> BrantaService:
    options = BrantaApiOptions(environment=environment)
    token = os.environ.get("BRANTA_INTEGRATION_METRICS_TOKEN")
    session = aiohttp.ClientSession(headers={"X-Branta-Integration-Token": token}) if token else None
    return BrantaService(options, client=BrantaClient(options, session=session))


@pytest.mark.timeout(TIMEOUT)
class TestProduction:
    ON_CHAIN = "bitcoin:bc1qu3k6geqdjncaarsu2vq56tt8php5vsug9kasmq"
    LIGHTNING = (
        "lightning:lnbc17760n1p4r4tqupp5yuapqmxldkc8smuwa6t8shkdg9gezulu0vc7htepfsvweph8kqfsdphgfexzmn5vysyge"
        "tkv4kx7ur9wgsyc6t8dp6xu6twvusy27rpd4cxcegcqzzsxq97zvuqsp53564rg6w4xjqy7jamcfqxyy83a0j8nzfs0wpevs3"
        "7t5ln49q6hrs9qxpqysgq47hpqmv34g25le8sceq9jdvul2nz7ucyu0vucv56nlfe40x7n3jsu8duxjrn6tgvdspt872crk9ze"
        "atafznm9c57m039z7wyx6g3njsqkchkdh"
    )
    BRANTA_ON_CHAIN = (
        "bitcoin:bc1q6745z6cy3u0k9nprurh3x804c4r7u3u8vxca2n"
        "?branta_id=Qy4e3KJ9yRs%2BVWq59aSTC6o%2F6vbCnw0v7ZutEs1mxjpGM2i5DgVVl7G0TwFO9CqQ1ws3zNqogQu%2B2%2Bx3U%2BQ8%2FSZtwgjezw"
        "%3D%3D&branta_secret=f9b0fd20-b402-4cd2-b68f-3ae3db52dbf5"
    )
    BRANTA_LIGHTNING = (
        "lightning:lnbc17760n1p4r4flypp5k56kq3v2935rl3glkqu9vngfueud2zj87hjcff3t0kn0yrge0pfqdzjgfexzmn5vysz6gz"
        "yv4mx2mr0wpjhygzvd9nksarwd9hxwgz6v4ex7gztdehhwmr9v3nk2gz90psk6urvv5cqzzsxq97zvuqsp5hut3t0l0s5mvp9yr"
        "06v4253kqtf452z6c65s6g9sga445hc03v6s9qxpqysgqqm430zkk9uymjgvllr3aha88hc6q59etxasfqswn8r8pfm3dstlpp46"
        "azv906xtcj3wzprxup5fxn65a5wymt7zzq9sw9qdzx8rgdhcpk80nrg"
    )
    BRANTA_UNIFIED = (
        "bitcoin:bc1qu3k6geqdjncaarsu2vq56tt8php5vsug9kasmq?lightning=lnbc17760n1p4r4tqupp5yuapqmxldkc8smuwa6t8"
        "shkdg9gezulu0vc7htepfsvweph8kqfsdphgfexzmn5vysygetkv4kx7ur9wgsyc6t8dp6xu6twvusy27rpd4cxcegcqzzsxq97zvu"
        "qsp53564rg6w4xjqy7jamcfqxyy83a0j8nzfs0wpevs37t5ln49q6hrs9qxpqysgq47hpqmv34g25le8sceq9jdvul2nz7ucyu0vu"
        "cv56nlfe40x7n3jsu8duxjrn6tgvdspt872crk9zeatafznm9c57m039z7wyx6g3njsqkchkdh"
        "&branta_id=%2BbcErHkjD6aDfvhegd1CPRgQQwes64aMIqPXCRBVKP88d982zJt7TUHTq%2B11O9ij9HFzXC%2BTvh%2ByFoECrv"
        "ZKpv%2FVuGGLIA%3D%3D&branta_secret=c4ba0501-059e-459b-9b11-64d97f158291"
    )
    NOT_FOUND = "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    TAMPERED = (
        "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        "?branta_id=Qy4e3KJ9yRs%2BVWq59aSTC6o%2F6vbCnw0v7ZutEs1mxjpGM2i5DgVVl7G0TwFO9CqQ1ws3zNqogQu%2B2%2Bx3U%2BQ8%2FSZtwgjezw"
        "%3D%3D&branta_secret=f9b0fd20-b402-4cd2-b68f-3ae3db52dbf5"
    )

    @pytest.fixture(autouse=True)
    def _service(self):
        self.service = make_service(BrantaEnvironment.Production)

    async def test_on_chain_plain_text_is_unknown(self):
        result = await self.service.verify(self.ON_CHAIN)
        assert result.status == VerifyStatus.Unknown
        assert result.payments is None

    async def test_lightning_matches(self):
        result = await self.service.verify(self.LIGHTNING)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_branta_on_chain_matches(self):
        result = await self.service.verify(self.BRANTA_ON_CHAIN)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_branta_lightning_matches(self):
        result = await self.service.verify(self.BRANTA_LIGHTNING)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_branta_unified_matches(self):
        result = await self.service.verify(self.BRANTA_UNIFIED)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_not_found_is_unknown(self):
        result = await self.service.verify(self.NOT_FOUND)
        assert result.status == VerifyStatus.Unknown
        assert result.payments is None

    async def test_tampered_is_tampered(self):
        result = await self.service.verify(self.TAMPERED)
        assert result.status == VerifyStatus.Tampered
        assert result.payments is None
        assert "#k-" not in result.verify_url


@pytest.mark.timeout(TIMEOUT)
class TestStaging:
    ON_CHAIN = "bitcoin:bc1qgw3dzmhnyvcswc9r0v0z0ajtp8ulm4nuyeahwr"
    BOLT11 = (
        "lightning:lnbc10u1p4w23tzpp50uc6g4020tt3ffp5xfpp83k0lcv2spytpymuupqrnsj0eth8jqgsdqhgfexzmn5vys8xarp"
        "va5kuecxq97zvuqsp5tj2a5fd84lhdddzfqz2lwmjqg7n9gp28yy5vtqd78muyzdt5tmsq9qypsqqcqpf6yv66fkcq609xzk0fc"
        "qx82hd7fsjhwrzj8xmq743v5lrtssrj95r94hyeumqeejgqvtxqy7ks7ec0uc5lc5zxg240xtwgzjtwkmh3aqqm8gyny"
    )
    BRANTA_ON_CHAIN = (
        "bitcoin:bc1qgw3dzmhnyvcswc9r0v0z0ajtp8ulm4nuyeahwr"
        "?branta_id=6SpYCe23r79x0t8rNvmjWqhrg8hen4xz%2FYSXhNJ9HLSYrTRPnm%2BSwAuf6NOKobnwE%2B3MQBNkyTnCtIWp"
        "KKX2E9ZUWVedig%3D%3D&branta_secret=05eb145d-b5cb-452a-9256-0bdfd9a15ffa"
    )
    TESTNET = (
        "bitcoin:tb1qshra2mlujc9wfscvn4d8aqpyqgxzl55853xg7s"
        "?branta_id=fa05KT1L6zIAYx2sHcImF3R5RilwMAXAvx%2F5u2YVBIdvnp30drV7bszFzvpdoA%2FeluN0PXbsxcsD38twzw4"
        "%2BL8MFoHxkGQ%3D%3D&branta_secret=0621110e-1ad6-483d-80b6-78697c9f6896"
    )
    ARK = "ark1qztwuhx7vpytv4dcfeqjsepx3kxstnarelmry2smrfdgt2dv87fas7gtqkk"
    SILENT_PAYMENT = (
        "sp1qqgste7k9hx0qftg6qmwlkqtwuy6cycyavzmzj85c6qdfhjdpdjtdgqjuexzk6murw56suy3e0rd2cgqvycxttddwsvgxe2usfpxumr70xc9pkqwv"
    )
    BRANTA_UNIFIED = (
        "bitcoin:bc1q6745z6cy3u0k9nprurh3x804c4r7u3u8vxca2n?lightning=lnbc10u1p4w23tzpp5s6jc8gvun27un7g7q9km"
        "h2vak78r83766heesd9fepa5s56hrpsqdqhgfexzmn5vys8xarpva5kuecxq97zvuqsp5gt4k9wwdgf85g066a05zrnlkh3jc2n"
        "g3mh9mw6yw7z03l4kmqzys9qypsqqcqpf7pk6xjfksy8sqhv24es2qgtp0e88wvt2gdv2zceealhjwh0memhzktgnfhdvzc9a6k"
        "t74w5jf5c8v9t20k38snawrgngr0sjw9a58fqqn9lwtq"
        "&branta_id=NxkrlFgIvGg6f8YZmFAf8qTUza8nXfn%2Bb9H3W7czFAo5Lp4cSpgRSmJgx7P9vaOYu7lkP6XXKvTshQfkXxxRrx"
        "J%2BE7zdpA%3D%3D&branta_secret=6acf2637-511a-4b89-ba2c-f5914d7e669c"
    )
    NOT_FOUND = "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    TAMPERED = (
        "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        "?branta_id=6SpYCe23r79x0t8rNvmjWqhrg8hen4xz%2FYSXhNJ9HLSYrTRPnm%2BSwAuf6NOKobnwE%2B3MQBNkyTnCtIWp"
        "KKX2E9ZUWVedig%3D%3D&branta_secret=05eb145d-b5cb-452a-9256-0bdfd9a15ffa"
    )

    @pytest.fixture(autouse=True)
    def _service(self):
        self.service = make_service(BrantaEnvironment.Staging)

    async def test_on_chain_plain_text_is_unknown(self):
        result = await self.service.verify(self.ON_CHAIN)
        assert result.status == VerifyStatus.Unknown
        assert result.payments is None

    async def test_bolt11_matches(self):
        result = await self.service.verify(self.BOLT11)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_branta_on_chain_matches(self):
        result = await self.service.verify(self.BRANTA_ON_CHAIN)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_testnet_matches(self):
        result = await self.service.verify(self.TESTNET)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_ark_matches(self):
        result = await self.service.verify(self.ARK)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_silent_payment_matches(self):
        result = await self.service.verify(self.SILENT_PAYMENT)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_branta_unified_matches(self):
        result = await self.service.verify(self.BRANTA_UNIFIED)
        assert result.status == VerifyStatus.Match
        assert result.payments

    async def test_not_found_is_unknown(self):
        result = await self.service.verify(self.NOT_FOUND)
        assert result.status == VerifyStatus.Unknown
        assert result.payments is None

    async def test_tampered_is_tampered(self):
        result = await self.service.verify(self.TAMPERED)
        assert result.status == VerifyStatus.Tampered
        assert result.payments is None
        assert "#k-" not in result.verify_url
