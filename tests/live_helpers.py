"""Shared helpers for gated live Guardrail tests."""
from __future__ import annotations

import os
from urllib.parse import urlencode

from branta.client import BrantaClient
from branta.enums import EVM_TOKEN_RAILS, BrantaEnvironment, DestinationType
from branta.options import BrantaApiOptions
from branta.service import BrantaService


def make_service(environment: BrantaEnvironment) -> BrantaService:
    options = BrantaApiOptions(
        environment=environment,
        api_key=os.environ.get("BRANTA_API_KEY"),
    )
    token = os.environ.get("BRANTA_INTEGRATION_METRICS_TOKEN") or None
    return BrantaService(
        options,
        client=BrantaClient(options, integration_metrics_token=token),
    )


def transfer_uri(destination_type: DestinationType, recipient: str, encrypted: str, secret: str) -> str:
    """ERC-681 transfer URI for one EVM rail, with the Branta params."""
    rail = next(rail for rail in EVM_TOKEN_RAILS if rail.type == destination_type)
    query = urlencode(
        {
            "address": recipient,
            "uint256": "1000000",
            "branta_id": encrypted,
            "branta_secret": secret,
        }
    )
    return f"ethereum:{rail.contract}@{rail.chain_id}/transfer?{query}"
