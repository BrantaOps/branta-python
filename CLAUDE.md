# Branta Python SDK

Feature-parity Python port of the Branta SDK. Mirrors the other Branta 4.x SDKs. A public method added or changed here has to be reflected across the SDK family.

## Package layout

- `branta/__init__.py` — public export (`BrantaService`, `PaymentBuilder`, `DestinationType`, `BrantaEnvironment`, `VerifyResult`, `BrantaApiOptions`, exceptions)
- `branta/service.py` — `BrantaService` (encrypt/decrypt around HTTP). `client.py` is the raw HTTP layer; do not call it from consumer code
- `branta/builder.py` — `PaymentBuilder`
- `branta/parser.py` — `QRParser` (internal)
- `branta/encryption.py` — AES-256-GCM
- `branta/serialization.py` — Guardrail JSON
- `tests/` — unit tests mock the client; live lookups / multi-rail round-trips / combos run only when `BRANTA_RUN_INTEGRATION=1` (API key required for write tests)

## Setup

```bash
pip install -e ".[dev]"
```

## Commands

- `pytest tests/` — unit tests; live lookups skipped unless `BRANTA_RUN_INTEGRATION=1`
- `BRANTA_RUN_INTEGRATION=1 pytest tests/test_integration.py` — live Guardrail lookups
- `BRANTA_RUN_INTEGRATION=1 BRANTA_API_KEY=… pytest tests/` — include multi-rail round-trips and live combos
- `coverage run -m pytest tests/ && coverage report` — with coverage

## Key behaviors to preserve

- **Unencrypted destinations are not supported.** `verify` is the only lookup. A raw on-chain address (including `tb1` / `bcrt1` / bare `0x`) is `unknown` and does not GET. `add_payment` encrypts every destination; types that cannot be encrypted throw.
- **`DestinationType` is only what `add_payment` accepts:** `bitcoin_address`, `bolt11`, `ark_address`, `silent_payment`, plus stable rails `usdt_polygon` / `usdc_polygon`, `usdt_ethereum` / `usdc_ethereum`, `usdt_bsc` / `usdc_bsc`, `usdt_tron`, `usdt_ton`, `usdt_solana` / `usdc_solana`. Pass stable types explicitly. BIP21 extras this SDK cannot encrypt (`lno`, `pay`, non-bolt11 `lightning`) make `verify()` return `unknown`. `usdc_ton` is deferred.
- **Chain URI verify** (`pol:`, `eth:`, `bsc:`, `tron:`, `ton:`, `sol:`) is match-if-any within that scheme's family; token is on `matched_destinations[].type`, not the scheme. A bare address is `unknown`.
- **`verify()` returns `VerifyResult`.** `match` includes `payments`, `matched_destinations`, and `verify_url`. `unknown`, `tampered`, and `incomplete` include only `verify_url`. A swapped address is `tampered`. A 404 is `unknown`. 5xx, 429, and no network are `incomplete`. `branta_id` / `branta_secret` with no payable destination is `unknown`. A bolt11 / Ark / silent-payment GET hit is `unknown` unless a destination of that type decrypts.
- **`verify_url` is always returned.** Format: `{api_origin}/v2/verify/{lookup}` plus a URL fragment built from per-destination encryption keys on `match`.
- **Encryption.** Bitcoin and stablecoin address rails use a caller-supplied secret (random UUID). bolt11, Ark, and silent payments use a key derived from a normalized hash of the value. `add_payment` encrypts a copy and leaves the caller `Payment` unchanged. Guardrail still receives `zk: true` and `zk_id` (`Destination.id`).
- **Description** lives in encrypted `metadata.description` and is lifted onto `payment.description` after decrypt. It is not posted or read as Guardrail's plaintext `description` field.
- **Public names.** Package entry exports `DestinationType` for rails — not `SECRET_KEY_URI_FAMILIES` or per-family helpers. `BrantaApiOptions` (`environment`, `api_key`, `hmac_secret`). `BrantaEnvironment`. Do not reintroduce `BrantaClientOptions`, `PrivacyMode`, `BrantaServerBaseUrl`, `set_zk`, or `get_payments_by_qr_code`.
- **`verify` parses first.** Multi-value payloads go through `QRParser` whether they came from a scan or a paste.
- **Never surface `unknown` or thrown errors to the user.** `tampered` is the exception: warn, do not show a verified card.
- **Domain validation.** Logo URLs on platform, light, parent, and child must match the API origin. Every payment in a GET response is checked. An empty logo skips that field only.

## Conventions

- Async throughout — `BrantaService` and `BrantaClient` methods are `async def`.
- Python snake_case for public attributes and methods.
- `BrantaService` takes one `BrantaApiOptions`. Inject `client`, `aes_encryption`, and `secret_generator` as keyword arguments in tests.
- The public API is whatever `branta/__init__.py` exports.
