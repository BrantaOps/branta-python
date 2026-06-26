from __future__ import annotations

import uuid


class GuidSecretGenerator:
    deterministic_nonce: bool = False

    def generate(self) -> str:
        return str(uuid.uuid4())
