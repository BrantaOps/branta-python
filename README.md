# Branta Python SDK

Python SDK for the [Branta](https://branta.pro) V2 API — payment destination lookup and registration with zero-knowledge encryption support.

## Installation

```bash
pip install branta
```

## Integration Guide

### Quick start

```python
import asyncio
from branta.enums import BrantaServerBaseUrl, PrivacyMode
from branta.options import BrantaClientOptions
from branta.v2 import BrantaService

options = BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Production,
    privacy=PrivacyMode.Strict,
)
service = BrantaService(options)

async def main():
    result = await service.get_payments_by_qr_code("bitcoin:bc1q...")
    if result.payments:
        print(result.payments[0].get_default_value())

asyncio.run(main())
```

### Privacy modes

| Mode | Behaviour |
|------|-----------|
| `PrivacyMode.Strict` (default) | Only ZK lookups. `get_payments()` raises `BrantaPaymentException` for plain addresses. `get_payments_by_qr_code()` returns empty for plain addresses. `add_payment()` raises if any destination has `is_zk=False`. |
| `PrivacyMode.Loose` | Both plain and ZK lookups are permitted. |

### Looking up a payment by QR code

```python
result = await service.get_payments_by_qr_code(qr_text)
# result.payments — list of Payment objects (empty if not found)
# result.verify_url — always populated; share with the payer to verify
```

Prefer `get_payments_by_qr_code` for QR-driven flows. It handles multi-destination payloads (`branta_id` / `branta_secret` fragments) automatically.

### Looking up a payment by destination value

```python
# Plain bitcoin address (requires PrivacyMode.Loose or will raise):
result = await service.get_payments("bc1q...")

# ZK-encrypted bitcoin address with secret:
result = await service.get_payments(encrypted_address, destination_encryption_key="my-secret")

# BOLT-11 invoice (hash-ZK — works in strict mode):
result = await service.get_payments("lnbc...")
```

### Registering a payment

```python
from branta.enums import DestinationType

builder = service.create_payment_builder()
payment = (
    builder
    .add_destination("bc1q...", DestinationType.BitcoinAddress).set_zk()
    .add_destination("lnbc...", DestinationType.Bolt11).set_zk()
    .set_description("Donation")
    .add_metadata("email", "donor@example.com")
    .build()
)

result = await service.add_payment(payment, BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Production,
    default_api_key="your-api-key",
    privacy=PrivacyMode.Strict,
))
# result.payment — the registered payment from the server
# result.secret — the random encryption key for the bitcoin address
# result.verify_url — share this URL to verify the payment
```

### Validating an API key

```python
is_valid = await service.is_api_key_valid(BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Production,
    default_api_key="your-api-key",
))
```

### For parent platforms

Choose a variant based on how API keys are structured. Shared key needs only an API key; per-client keys also require HMAC.

**Shared key — one API key covers all children (Recommended)**

Construct with a single API key; identify the child platform per-payment. Do not include `hmac_secret`.

```python
options = BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Production,
    default_api_key="<shared-api-key>",
    privacy=PrivacyMode.Strict,
)
service = BrantaService(options)

payment = (
    service.create_payment_builder()
    .add_destination("bc1q...", DestinationType.BitcoinAddress).set_zk()
    .set_description("Order #1234")
    .set_child_platform("ChildBrand", logo_url="https://example.com/logo.png")
    .build()
)

result = await service.add_payment(payment)
```

**Per-client keys — each child has its own API key**

Construct the service with the parent HMAC secret only; pass each child's API key per-call.

```python
options = BrantaClientOptions(
    base_url=BrantaServerBaseUrl.Production,
    hmac_secret="<hmac-secret>",
    privacy=PrivacyMode.Strict,
)
service = BrantaService(options)

payment = (
    service.create_payment_builder()
    .add_destination("bc1q...", DestinationType.BitcoinAddress).set_zk()
    .build()
)

result = await service.add_payment(
    payment,
    BrantaClientOptions(default_api_key="<child-api-key>"),
)
```

### Per-call option overrides

Every public method accepts an optional `BrantaClientOptions` parameter that overrides the service's default options for that call only:

```python
service = BrantaService(default_options)
result = await service.get_payments("lnbc...", options=override_options)
```

## ZK destination types

| Type | Encryption |
|------|-----------|
| `BitcoinAddress` | Random secret (GUID) per payment |
| `Bolt11` | Deterministic: SHA256 of lowercase invoice |
| `ArkAddress` | Deterministic: SHA256 of lowercase address |
| `SilentPayment` | Deterministic: SHA256 of lowercase address |

## Development

```bash
pip install -e ".[dev]"
pytest tests/ --ignore=tests/test_integration.py     # unit tests
pytest tests/test_integration.py                     # integration (requires network)
coverage run -m pytest tests/ --ignore=tests/test_integration.py && coverage report
```
