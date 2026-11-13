# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.3.1] - 2026-11-13

### Fixed
- HTTP calls (GET, POST, health-check) use a 30s `aiohttp` timeout. A verify GET that times out returns `incomplete`.

## [4.3.0] - 2026-11-12

### Added
- Multi-rail stablecoin destination types for `add_payment` / `verify`: `usdt_ethereum`, `usdc_ethereum`, `usdt_bsc`, `usdc_bsc`, `usdt_tron`, `usdt_ton`, `usdt_solana`, `usdc_solana`.
- Chain URI schemes `eth:`, `bsc:`, `tron:`, `ton:`, and `sol:` follow the existing `pol:` pattern: secret-key encrypt, match-if-any within the scheme family, token on the matched destination type. Bare addresses remain `unknown`.

### Changed
- Package entry exports only the consumer surface. Rail-family helpers (`SECRET_KEY_URI_FAMILIES`, per-family tuples, `is_secret_key_address_type`, and the former `is_polygon_evm_destination_type`) stay internal — import `DestinationType` from `branta` for POST/verify.
- This release matches `@branta-ops/branta` 4.3.0.

### Notes
- `usdc_ton` is deferred until a platform names a concrete TON USDC jetton.

## [4.2.0] - 2026-11-10

### Added
- `DestinationType.UsdtPolygon` for Polygon USDT. `add_payment` encrypts the recipient with a random secret (same pattern as bitcoin). `verify` parses `pol:` URIs with `branta_id` / `branta_secret`; other query params (`value`, `currency`, `user`) are ignored for binding. A bare `0x` address is `unknown`. EVM address compare is case-insensitive.
- `DestinationType.UsdcPolygon` for Polygon USDC. Same secret-key encrypt / `pol:` verify path as `usdt_polygon`. Token is the destination type on the payment; `pol:` remains the Polygon EVM scheme for both.
- `POLYGON_EVM_DESTINATION_TYPES`, `is_polygon_evm_destination_type`, and `is_secret_key_address_type`.
- `VerifyResult.matched_destinations` on `match` — decrypted rails that bound the scan (token for `pol:` is on `type`).

### Changed
- `verify` of a `pol:` URI binds any Polygon EVM family member whose decrypted address matches (match-if-any).
- `pol:` parsing does not stamp a token `DestinationType` on the QR address. The scheme maps to the Polygon EVM family for verify; the token still comes from the matched payment destination.
- `verify` swap-checks only the secret-key rail family that matches the QR scheme, so a payment with both bitcoin and `usdt_polygon` no longer returns `tampered` for a valid single-rail QR.
- This release matches `@branta-ops/branta` / Branta.NET / branta-go / branta-swift / branta-kotlin 4.2.0.

## [4.0.1] - 2026-11-01

### Fixed
- `verify_url` fragment names and values are percent-encoded, so a crafted id or secret cannot add parameters.
- `verify()` of a bolt11, Ark, or silent payment is `tampered` when the decrypted plaintext is not the scanned value. Case differences still match.

### Changed
- This release matches `@branta-ops/branta` 4.0.5.

## [4.0.0] - 2026-11-01

### Removed
- **BREAKING:** `PrivacyMode` and the `privacy` option. Every destination is encrypted. On-chain lookups need `branta_id` / `branta_secret`. bolt11, Ark, and silent payments still resolve from the value.
- **BREAKING:** `PaymentBuilder.set_zk()` and `Destination.is_zk`. `add_destination` assigns `Destination.id`. Guardrail still receives `zk: true` and `zk_id`.
- **BREAKING:** `get_payments` and `get_payments_by_qr_code`. Call `verify(input)` for a QR scan or a paste.
- **BREAKING:** `verify()` returns `VerifyResult` with `status` of `match`, `unknown`, `tampered`, or `incomplete`. A swapped address is `tampered`. `payments` is present only on `match`. `PaymentsResult` and `BrantaPaymentExceptionReason` are gone.
- **BREAKING:** `DestinationType.Bolt12`, `LnUrl`, `TetherAddress`, and `LnAddress`. `DestinationType` is what `add_payment` accepts: `bitcoin_address`, `bolt11`, `ark_address`, `silent_payment`.
- **BREAKING:** `BrantaClientOptions` is `BrantaApiOptions`. `base_url` is `environment`. `BrantaServerBaseUrl` is `BrantaEnvironment`. `default_api_key` is `api_key`.
- **BREAKING:** `QRParseException`, `Payment.btc_pay_server_plugin_version`, and `Payment.get_default_value`.
- **BREAKING:** `BrantaClient`, `QRParser`, `AesEncryption`, and `GuidSecretGenerator` are not part of the public package export. The `branta.v2` package path is gone. Import from `branta`. Guardrail HTTP paths remain `/v2/...`.

### Added
- `verify()` status `incomplete` when the lookup does not finish (5xx, 429, or no network). A 404 is `unknown`.

### Fixed
- `verify()` of a bolt11, Ark, or silent payment is `unknown` unless a destination of that type decrypts.
- `verify()` of `branta_id` / `branta_secret` with no payable destination is `unknown` and does not look the record up.
- A raw on-chain address, including `tb1` / `bcrt1`, is `unknown` and is not fetched.
- `add_payment` encrypts a copy of the caller's `Payment`. A failed post leaves that object reusable, so a retry encrypts the original address or invoice.

### Changed
- `set_description` writes `metadata.description`. The SDK does not POST or GET Guardrail's plaintext `description` field. After metadata decrypt, `payment.description` is lifted from `metadata.description`.
- This release matches `@branta-ops/branta` 4.0.4.

## [3.2.5] - 2026-10-29

### Fixed
- `get_payments_by_qr_code` requires every payable instruction in a QR code to match a decrypted destination before it returns a payment. A swapped address with a rewritten `branta_secret`, an added `lightning`/`ark`/`sp` leg, or a conflicting `bc=`/`tb=` no longer comes back as verified. `bolt12`, `lno=`, `pay=`, and LNURL instructions return no payments (ported from `branta-js` PR #78)

## [3.2.4] - 2026-10-28

### Fixed
- `get_payments_by_qr_code` strips the same control characters as `urlparse` — tab, line feed, and carriage return anywhere, plus leading C0 controls — before it types a QR destination. A control byte inside `bitcoin:` no longer leaves the address untyped, so a swapped address still raises `Tampered`.

## [3.2.3] - 2026-10-28

### Added
- Recognize signet and regtest Ark addresses (`tark1`) as `ark_address`, alongside mainnet `ark1`. Strict-mode hash-ZK lookup and registration treat them the same way as `ark1`.

## [3.2.2] - 2026-09-30

### Fixed
- Fixed a same-origin validation gap: if the first payment in a `get_payments` response had no `platform_logo_url`, validation silently stopped checking every later payment's logo URLs entirely. Logo-URL checks now run independently per payment, and now also cover `platform_logo_light_url`, `parent_platform.logo_url`/`logo_light_url`, and `child_platform.logo_url`/`logo_light_url` (previously only `platform_logo_url` was checked)

## [3.2.1] - 2026-08-29

### Fixed
- `get_payments_by_qr_code` now verifies that the plaintext Bitcoin address parsed from a scanned QR code matches the address decrypted via `branta_id`/`branta_secret`, raising `BrantaPaymentException` with `reason=BrantaPaymentExceptionReason.Tampered` on mismatch. Closes a gap where an attacker could swap the visible address in a `bitcoin:` URI while leaving a legitimate, verified `branta_id`/`branta_secret` pair untouched (ported from `branta-js` 3.2.1)

## [3.2.0] - 2026-06-26

### Added
- `PaymentBuilder.set_child_platform(name, logo_url, logo_light_url)` — allows master-switch platforms to associate a child platform with a payment on POST
- `Payment.child_platform` field (optional `Platform`) to hold the child platform data before submission
- Removed tracked `__pycache__` files and ensured they are covered by `.gitignore`

## [3.1.0] - 2026-06-25

### Added
- Initial release of the Branta Python SDK
- Feature-parity port of `branta-js` 3.1.4 and `branta-dotnet` 3.1.6
- `BrantaService` with `get_payments`, `get_payments_by_qr_code`, `add_payment`, and `is_api_key_valid`
- `PaymentBuilder` fluent builder for constructing `Payment` objects
- `QRParser` for parsing Bitcoin and Lightning URI QR codes
- AES-256-GCM encryption with deterministic and random nonce modes
- Zero-knowledge (ZK) destination support for Bitcoin addresses, BOLT-11, Ark, and silent payments
- Metadata DEK-envelope encryption
- `PrivacyMode.Strict` (default) and `PrivacyMode.Loose` enforcement
- HMAC-SHA256 signing support for parent platform use
- Full type annotations and async/await throughout
- Unit and integration tests with full branch coverage
