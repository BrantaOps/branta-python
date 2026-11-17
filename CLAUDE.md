# Branta Python SDK

Python SDK published on PyPI as `branta`. Consumers (wallets, platforms, parent platforms) call `BrantaService` to look up or post payments to Branta's V2 API. `README.md` is the install, constructor, and samples guide.

## Behavior contract

What `verify` returns and how ERC-681 is parsed: [Status rules](https://developer.branta.pro/setup/send/status-rules). Which rails encrypt with what key: [Encryption](https://developer.branta.pro/setup/receive/encryption). Send handling is on [Send](https://developer.branta.pro/setup/send), and the type list on [Destination types](https://developer.branta.pro/destination-types). Do not restate them here. Change the docs first, then the SDK.

Invariants that break silently. Check them before you change `verify` or `addPayment`:

- A raw on-chain address (including `tb1` / `bcrt1` / bare `0x`) is `unknown` and does not GET.
- A swapped address is `tampered`. `unknown`, `tampered`, and `incomplete` are returned, never thrown.
- The token is `matchedDestinations[].type`, never the URI scheme.
- A logo-domain mismatch throws. Every other lookup failure is a status.
- `addPayment` encrypts a copy and leaves the caller's `Payment` unchanged.
- Keep parity with every 4.x Branta SDK. A public method added or changed here is mirrored in each of them.

## Python specifics

- The contract's names are snake_case here: `add_payment`, `matched_destinations`, `verify_url`.
- `Destination.id` is sent as `zk_id`. `zk: true` is always sent.
- `verify` parses first. Multi-value payloads go through `QRParser` whether they came from a scan or a paste.
- `DestinationType` is only what `add_payment` accepts. It also includes `usdt_tron`, `usdt_ton`, `usdt_solana`, and `usdc_solana`. They can be posted but no URI verifies them, and they are not on the public Destination types page. There is no `usdc_ton`.
- Do not reintroduce `BrantaClientOptions`, `PrivacyMode`, `BrantaServerBaseUrl`, `set_zk`, or `get_payments_by_qr_code`.

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

## Conventions

- Async throughout — `BrantaService` and `BrantaClient` methods are `async def`.
- Python snake_case for public attributes and methods.
- `BrantaService` takes one `BrantaApiOptions` (`environment`, `api_key`, `hmac_secret`). Inject `client`, `aes_encryption`, and `secret_generator` as keyword arguments in tests.
- The public API is whatever `branta/__init__.py` exports. The rail table (`EVM_TOKEN_RAILS`, `evm_token_type`) and `is_secret_key_address_type` stay internal.
