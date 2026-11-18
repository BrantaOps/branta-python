# branta

Python SDK for [Branta](https://developer.branta.pro).

Status handling and parent platforms are in the [developer docs](https://developer.branta.pro).

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
        # For EVM stablecoins, the token is on result.matched_destinations[i].type.
        # Pay from matched_destinations, not from the raw QR.
        print(payment.destinations[0].value, result.verify_url)
    elif result.status == VerifyStatus.Tampered:
        # Destination was altered. Warn. Do not show a verified card.
        print(result.verify_url)
    elif result.status == VerifyStatus.Incomplete:
        # Branta could not complete the check. Tell the user. Do not block send.
        print(result.verify_url)
    # VerifyStatus.Unknown: not in Branta. Show nothing.


asyncio.run(main("bitcoin:bc1q…?branta_id=…&branta_secret=…"))
```

Rules for each status: [Status rules](https://developer.branta.pro/setup/send/status-rules). Supported types: [Destination types](https://developer.branta.pro/destination-types).

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
        .set_ttl(600)  # seconds
        .build()
    )
    result = await service.add_payment(payment)
    # Store result.secret with the invoice. Put branta_id and branta_secret on the QR.
    # Link the sender to result.verify_url.
    print(result.secret, result.verify_url)


asyncio.run(main())
```

`add_payment` accepts the types on [Destination types](https://developer.branta.pro/destination-types). Pass the type for stablecoins. A bare address is not auto-detected. `UsdtTron`, `UsdtTon`, `UsdtSolana`, and `UsdcSolana` also encrypt and post, but no URI verifies them.

## Per-call options

`verify`, `add_payment`, and `is_api_key_valid` take an optional `BrantaApiOptions` (`environment`, `api_key`) that overrides the constructor for that call.

[Changelog](CHANGELOG.md)
