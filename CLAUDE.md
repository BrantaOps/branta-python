# Branta Python SDK

Feature-parity Python port of the Branta SDK. Mirrors `branta-js` and `branta-dotnet` — any public API change in one must be reflected here and in the other two.

## Package layout

- `branta/` — top-level package; re-exports all public symbols
- `branta/enums.py` — `BrantaServerBaseUrl`, `DestinationType`, `PrivacyMode`
- `branta/exceptions.py` — `BrantaPaymentException`, `QRParseException`
- `branta/models.py` — `Payment`, `Destination`, `Platform`, `PaymentsResult`, `AddPaymentResult`
- `branta/options.py` — `BrantaClientOptions`
- `branta/extensions.py` — shared helper functions (hash, fragment, type detection)
- `branta/v2/service.py` — `BrantaService` (orchestrates ZK encrypt/decrypt around HTTP)
- `branta/v2/client.py` — `BrantaClient` (raw HTTP; do not call directly from consumer code)
- `branta/v2/builder.py` — `PaymentBuilder`
- `branta/v2/parser.py` — `QRParser`
- `branta/v2/encryption.py` — `AesEncryption` (static), `AesEncryptionService` (instance wrapper)
- `branta/v2/secret_generator.py` — `GuidSecretGenerator`
- `branta/v2/serialization.py` — snake_case JSON serialization helpers
- `tests/` — mirrors `branta/`; unit tests use mocked client + AES; integration tests hit live endpoints

## Setup

```bash
pip install -e ".[dev]"
```

## Commands

- `pytest tests/ --ignore=tests/test_integration.py` — run unit tests (no network)
- `pytest tests/test_integration.py` — run integration tests (requires network)
- `coverage run -m pytest tests/ --ignore=tests/test_integration.py && coverage report` — with coverage
- `pip install -e .` / `pip publish` — publish to PyPI (requires `twine`)

## Key behaviors to preserve

- **`PrivacyMode.Strict` is the default.** `get_payments` throws `BrantaPaymentException` for plain bitcoin addresses; `get_payments_by_qr_code` returns an empty `PaymentsResult`. `add_payment` throws if any destination has `is_zk=False`.
- **`verify_url` is always returned**, even on a miss. Format: `{base_url}/v2/verify/{lookup}` plus `#k-{zk_id}={key}` fragments.
- **ZK encryption:** Bitcoin addresses use a random secret (GUID); hash-ZK types (bolt11, ark, silent_payment) use a deterministic key from SHA256(normalized value). `add_payment` mutates `payment.destinations[*].value` to the encrypted form before POSTing.
- **Metadata DEK-envelope:** If a payment has metadata and any ZK destination, a separate DEK is generated, metadata is encrypted with it, and the DEK is encrypted per-destination.
- **Never surface lookup failures.** Swallow decryption errors; leave `is_encrypted=True` and value unchanged.
- **Domain validation.** `platform_logo_url` must match `base_url` domain.

## Conventions

- Async throughout — `BrantaService` and `BrantaClient` methods are all `async def`.
- Python snake_case for all public attribute and method names.
- Inject `client`, `aes_encryption`, `secret_generator` into `BrantaService` for testing.
- Keep feature-parity with `branta-js` and `branta-dotnet`: any new method, option, or enum value added here must be reflected in both.
