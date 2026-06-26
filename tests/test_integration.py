"""
Integration tests against live Branta endpoints.

Run with: pytest tests/test_integration.py -v
These tests require network access. They are skipped when BRANTA_SKIP_INTEGRATION
is set to any value, and will be automatically skipped if aiohttp is not installed.
"""
from __future__ import annotations

import os

import pytest

from branta.enums import BrantaServerBaseUrl, PrivacyMode
from branta.options import BrantaClientOptions
from branta.v2.service import BrantaService

pytestmark = pytest.mark.skipif(
    os.environ.get("BRANTA_SKIP_INTEGRATION") is not None,
    reason="Integration tests skipped (BRANTA_SKIP_INTEGRATION set)",
)

TIMEOUT = 15


def make_service(base_url: BrantaServerBaseUrl, privacy: PrivacyMode) -> BrantaService:
    return BrantaService(BrantaClientOptions(base_url=base_url, privacy=privacy))


# ===== Production — Loose =====

@pytest.mark.timeout(TIMEOUT)
class TestProductionLoose:
    ON_CHAIN = "bitcoin:bc1qu3k6geqdjncaarsu2vq56tt8php5vsug9kasmq"
    LIGHTNING = (
        "lightning:lnbc17760n1p4r4tqupp5yuapqmxldkc8smuwa6t8shkdg9gezulu0vc7htepfsvweph8kqfsdphgfexzmn5vysyge"
        "tkv4kx7ur9wgsyc6t8dp6xu6twvusy27rpd4cxcegcqzzsxq97zvuqsp53564rg6w4xjqy7jamcfqxyy83a0j8nzfs0wpevs3"
        "7t5ln49q6hrs9qxpqysgq47hpqmv34g25le8sceq9jdvul2nz7ucyu0vucv56nlfe40x7n3jsu8duxjrn6tgvdspt872crk9ze"
        "atafznm9c57m039z7wyx6g3njsqkchkdh"
    )
    ZK_ON_CHAIN = (
        "bitcoin:bc1q6745z6cy3u0k9nprurh3x804c4r7u3u8vxca2n"
        "?branta_id=z15b5EsbP5LHJrFco38%2BFp%2BHVaiopAY676NCKek8e1Q%2B4a370TyYhvloS8uLCUHfJ4CzeI%2FbOFmFDGp"
        "AQszB0gu1pJ1HOQ%3D%3D&branta_secret=c6e9eb30-6258-4432-9847-bdcc4fd4b0db"
    )
    ZK_LIGHTNING = (
        "lightning:lnbc17760n1p4r4flypp5k56kq3v2935rl3glkqu9vngfueud2zj87hjcff3t0kn0yrge0pfqdzjgfexzmn5vysz6gz"
        "yv4mx2mr0wpjhygzvd9nksarwd9hxwgz6v4ex7gztdehhwmr9v3nk2gz90psk6urvv5cqzzsxq97zvuqsp5hut3t0l0s5mvp9yr"
        "06v4253kqtf452z6c65s6g9sga445hc03v6s9qxpqysgqqm430zkk9uymjgvllr3aha88hc6q59etxasfqswn8r8pfm3dstlpp46"
        "azv906xtcj3wzprxup5fxn65a5wymt7zzq9sw9qdzx8rgdhcpk80nrg"
    )
    NOT_FOUND = "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

    @pytest.fixture(autouse=True)
    def _service(self):
        self.service = make_service(BrantaServerBaseUrl.Production, PrivacyMode.Loose)

    async def test_on_chain_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ON_CHAIN)
        assert len(result.payments) > 0

    async def test_lightning_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.LIGHTNING)
        assert len(result.payments) > 0

    async def test_zk_on_chain_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_ON_CHAIN)
        assert len(result.payments) > 0

    async def test_zk_lightning_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_LIGHTNING)
        assert len(result.payments) > 0

    async def test_not_found_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.NOT_FOUND)
        assert len(result.payments) == 0


# ===== Production — Strict =====

@pytest.mark.timeout(TIMEOUT)
class TestProductionStrict:
    ON_CHAIN = "bitcoin:bc1qu3k6geqdjncaarsu2vq56tt8php5vsug9kasmq"
    LIGHTNING = (
        "lightning:lnbc17760n1p4r4tqupp5yuapqmxldkc8smuwa6t8shkdg9gezulu0vc7htepfsvweph8kqfsdphgfexzmn5vysyge"
        "tkv4kx7ur9wgsyc6t8dp6xu6twvusy27rpd4cxcegcqzzsxq97zvuqsp53564rg6w4xjqy7jamcfqxyy83a0j8nzfs0wpevs3"
        "7t5ln49q6hrs9qxpqysgq47hpqmv34g25le8sceq9jdvul2nz7ucyu0vucv56nlfe40x7n3jsu8duxjrn6tgvdspt872crk9ze"
        "atafznm9c57m039z7wyx6g3njsqkchkdh"
    )
    ZK_ON_CHAIN = (
        "bitcoin:bc1q6745z6cy3u0k9nprurh3x804c4r7u3u8vxca2n"
        "?branta_id=z15b5EsbP5LHJrFco38%2BFp%2BHVaiopAY676NCKek8e1Q%2B4a370TyYhvloS8uLCUHfJ4CzeI%2FbOFmFDGp"
        "AQszB0gu1pJ1HOQ%3D%3D&branta_secret=c6e9eb30-6258-4432-9847-bdcc4fd4b0db"
    )
    ZK_LIGHTNING = (
        "lightning:lnbc17760n1p4r4flypp5k56kq3v2935rl3glkqu9vngfueud2zj87hjcff3t0kn0yrge0pfqdzjgfexzmn5vysz6gz"
        "yv4mx2mr0wpjhygzvd9nksarwd9hxwgz6v4ex7gztdehhwmr9v3nk2gz90psk6urvv5cqzzsxq97zvuqsp5hut3t0l0s5mvp9yr"
        "06v4253kqtf452z6c65s6g9sga445hc03v6s9qxpqysgqqm430zkk9uymjgvllr3aha88hc6q59etxasfqswn8r8pfm3dstlpp46"
        "azv906xtcj3wzprxup5fxn65a5wymt7zzq9sw9qdzx8rgdhcpk80nrg"
    )
    NOT_FOUND = "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

    @pytest.fixture(autouse=True)
    def _service(self):
        self.service = make_service(BrantaServerBaseUrl.Production, PrivacyMode.Strict)

    async def test_on_chain_plain_text_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.ON_CHAIN)
        assert len(result.payments) == 0

    async def test_lightning_plain_text_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.LIGHTNING)
        assert len(result.payments) == 0

    async def test_zk_on_chain_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_ON_CHAIN)
        assert len(result.payments) > 0

    async def test_zk_lightning_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_LIGHTNING)
        assert len(result.payments) > 0

    async def test_not_found_plain_text_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.NOT_FOUND)
        assert len(result.payments) == 0


# ===== Staging — Loose =====

@pytest.mark.timeout(TIMEOUT)
class TestStagingLoose:
    ON_CHAIN = "bitcoin:bc1qgw3dzmhnyvcswc9r0v0z0ajtp8ulm4nuyeahwr"
    LIGHTNING = (
        "lightning:lnbc25830n1p4quq9ppp5zszvpgxtu6uwyur6sf7rayc0meqprqlkv30xjzclh6nzm7gavd8sdzh2d6xzemfdenjqsnjv"
        "9h8gcfq95sygetkv4kx7ur9wgsyc6t8dp6xu6twvusy27rpd4cxcefq9pfhgct8d9hxw2gcqzzsxqzursp5fcfx5st7x8rgxra42"
        "j47hskmzkcz96mx84xcnvs9lpsmjyzqhw2q9qxpqysgq06lxdc93jjpuqsal9unlfct6wuv0v53yxa8kksl85g3qdw7qks7z9jkq3"
        "9c6wgzar72luwd38sfj0klyqv0zgns4rq7nafnd8qeuudcqql7at4"
    )
    ZK_ON_CHAIN = (
        "bitcoin:bc1q6745z6cy3u0k9nprurh3x804c4r7u3u8vxca2n"
        "?branta_id=z15b5EsbP5LHJrFco38%2BFp%2BHVaiopAY676NCKek8e1Q%2B4a370TyYhvloS8uLCUHfJ4CzeI%2FbOFmFDGp"
        "AQszB0gu1pJ1HOQ%3D%3D&branta_secret=c6e9eb30-6258-4432-9847-bdcc4fd4b0db"
    )
    ZK_LIGHTNING = (
        "lightning:lnbc25840n1p4qml83pp5aztzddx4k87m0wkd6wmgxr9753400mcj7sa89sa392krmueqv9qqdz92d6xzemfdenjqsnjv"
        "9h8gcfq95s9xarpva5kueeqtf9jqsn0d36zqvf3ypzhsctdwpkx2cqzzsxqzursp5c6dt82gqpn5vucmqtctur0p3cuur6xqgc63"
        "48wtz7adtgug9uf2q9qxpqysgq5yt6x946w3664th4h02pug9yhgszpznqyfwzndjk2sxe0878slqkdhgce4mr5ky2ux4gy4yt0vs"
        "y536tencls8fvu5wdzyaq548yf4qqu0lyg7"
    )
    NOT_FOUND = "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

    @pytest.fixture(autouse=True)
    def _service(self):
        self.service = make_service(BrantaServerBaseUrl.Staging, PrivacyMode.Loose)

    async def test_on_chain_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ON_CHAIN)
        assert len(result.payments) > 0

    async def test_lightning_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.LIGHTNING)
        assert len(result.payments) > 0

    async def test_zk_on_chain_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_ON_CHAIN)
        assert len(result.payments) > 0

    async def test_zk_lightning_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_LIGHTNING)
        assert len(result.payments) > 0

    async def test_not_found_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.NOT_FOUND)
        assert len(result.payments) == 0


# ===== Staging — Strict =====

@pytest.mark.timeout(TIMEOUT)
class TestStagingStrict:
    ON_CHAIN = "bitcoin:bc1qgw3dzmhnyvcswc9r0v0z0ajtp8ulm4nuyeahwr"
    ZK_ON_CHAIN = (
        "bitcoin:bc1q6745z6cy3u0k9nprurh3x804c4r7u3u8vxca2n"
        "?branta_id=z15b5EsbP5LHJrFco38%2BFp%2BHVaiopAY676NCKek8e1Q%2B4a370TyYhvloS8uLCUHfJ4CzeI%2FbOFmFDGp"
        "AQszB0gu1pJ1HOQ%3D%3D&branta_secret=c6e9eb30-6258-4432-9847-bdcc4fd4b0db"
    )
    ZK_LIGHTNING = (
        "lightning:lnbc25840n1p4qml83pp5aztzddx4k87m0wkd6wmgxr9753400mcj7sa89sa392krmueqv9qqdz92d6xzemfdenjqsnjv"
        "9h8gcfq95s9xarpva5kueeqtf9jqsn0d36zqvf3ypzhsctdwpkx2cqzzsxqzursp5c6dt82gqpn5vucmqtctur0p3cuur6xqgc63"
        "48wtz7adtgug9uf2q9qxpqysgq5yt6x946w3664th4h02pug9yhgszpznqyfwzndjk2sxe0878slqkdhgce4mr5ky2ux4gy4yt0vs"
        "y536tencls8fvu5wdzyaq548yf4qqu0lyg7"
    )
    NOT_FOUND = "bitcoin:bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"

    @pytest.fixture(autouse=True)
    def _service(self):
        self.service = make_service(BrantaServerBaseUrl.Staging, PrivacyMode.Strict)

    async def test_on_chain_plain_text_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.ON_CHAIN)
        assert len(result.payments) == 0

    async def test_zk_on_chain_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_ON_CHAIN)
        assert len(result.payments) > 0

    async def test_zk_lightning_returns_payment(self):
        result = await self.service.get_payments_by_qr_code(self.ZK_LIGHTNING)
        assert len(result.payments) > 0

    async def test_not_found_plain_text_returns_empty(self):
        result = await self.service.get_payments_by_qr_code(self.NOT_FOUND)
        assert len(result.payments) == 0
