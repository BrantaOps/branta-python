# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
