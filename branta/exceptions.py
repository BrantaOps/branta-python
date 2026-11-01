from enum import Enum


class BrantaPaymentExceptionReason(str, Enum):
    CryptoUnavailable = "crypto_unavailable"


class BrantaPaymentException(Exception):
    def __init__(self, message: str, reason: "BrantaPaymentExceptionReason | None" = None) -> None:
        super().__init__(message)
        self.reason = reason


class IncompleteError(Exception):
    pass
