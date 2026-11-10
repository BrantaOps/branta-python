"""Shared helpers for gated live Guardrail tests."""
from __future__ import annotations

import os
from urllib.parse import urlencode

import aiohttp

from branta.client import BrantaClient
from branta.enums import BrantaEnvironment
from branta.options import BrantaApiOptions
from branta.service import BrantaService


def make_service(environment: BrantaEnvironment) -> BrantaService:
    options = BrantaApiOptions(
        environment=environment,
        api_key=os.environ.get("BRANTA_API_KEY"),
    )
    token = os.environ.get("BRANTA_INTEGRATION_METRICS_TOKEN")
    session = aiohttp.ClientSession(headers={"X-Branta-Integration-Token": token}) if token else None
    return BrantaService(options, client=BrantaClient(options, session=session))


def pol_uri(recipient: str, encrypted: str, secret: str) -> str:
    query = urlencode(
        {
            "value": "50",
            "user": "send",
            "currency": "USD",
            "branta_id": encrypted,
            "branta_secret": secret,
        }
    )
    return f"pol:{recipient}?{query}"
