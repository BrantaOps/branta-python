# branta

Python SDK for [Branta](https://developer.branta.pro).

Use `verify()` on send and `add_payment()` on receive. Status handling and parent platforms are in the [developer docs](https://developer.branta.pro).

## Install

```bash
pip install branta
```

## Send

```python
import asyncio
from branta import BrantaApiOptions, BrantaEnvironment, BrantaService, VerifyStatus

service = BrantaService(BrantaApiOptions(environment=BrantaEnvironment.Production))


async def main(scanned_or_pasted: str) -> None:
    result = await service.verify(scanned_or_pasted)

    if result.status == VerifyStatus.Match:
        payment = result.payments[0]
        # Show the card. Link it to result.verify_url.
        # For chain URIs (pol:/eth:/…), token is on result.matched_destinations[i].type
        # — do not infer it from the scheme.
        print(payment.destinations[0].value, result.verify_url)
    elif result.status == VerifyStatus.Tampered:
        # Destination was altered. Warn. Do not show a verified card.
        print(result.verify_url)
    elif result.status == VerifyStatus.Incomplete:
        # 5xx, 429, or unreachable. Tell the user. Do not treat this as unknown.
        print(result.verify_url)
    # VerifyStatus.Unknown: not in Branta. Show nothing.


asyncio.run(main("bitcoin:bc1q…?branta_id=…&branta_secret=…"))
```

`environment` is `Production` on release and `Staging` everywhere else.

On-chain Bitcoin needs a `bitcoin:` URI with `branta_id` / `branta_secret`. Stablecoin rails need a chain URI (`pol:`, `eth:`, `bsc:`, `tron:`, `ton:`, `sol:`) with the same params — token is on `matched_destinations[].type`, not the scheme. bolt11, Ark, and silent payments resolve from the value. A bare address (including bare `0x`) is `unknown`.

A 404 is `unknown`. 5xx, 429, or no network is `incomplete`.

## Receive

```python
import asyncio
from branta import BrantaApiOptions, BrantaEnvironment, BrantaService, DestinationType

service = BrantaService(
    BrantaApiOptions(environment=BrantaEnvironment.Production, api_key="<api-key>")
)


async def main() -> None:
    payment = (
        service.create_payment_builder()
        .set_description("Invoice #12345")
        .add_destination("bc1q…", DestinationType.BitcoinAddress)
        # Stables: pass the rail type explicitly — bare 0x is not auto-detected.
        # .add_destination("0x…", DestinationType.UsdtEthereum)
        .set_ttl(600)  # seconds
        .build()
    )
    result = await service.add_payment(payment)
    # Store result.secret with the invoice.
    # Put branta_id and branta_secret on the invoice QR (bitcoin:… or pol:/eth:/…).
    print(result.secret, result.verify_url)


asyncio.run(main())
```

`add_payment` encrypts a copy. The `Payment` you pass in stays plaintext, so a failed post can be retried. It accepts `BitcoinAddress`, `Bolt11`, `ArkAddress`, `SilentPayment`, and the named stable rails (`UsdtPolygon` / `UsdcPolygon`, `UsdtEthereum` / `UsdcEthereum`, `UsdtBsc` / `UsdcBsc`, `UsdtTron`, `UsdtTon`, `UsdtSolana` / `UsdcSolana`).

## Per-call options

`verify`, `add_payment`, and `is_api_key_valid` take an optional `BrantaApiOptions` (`environment`, `api_key`, `hmac_secret`) that overrides the constructor for that call.

[Changelog](CHANGELOG.md)
