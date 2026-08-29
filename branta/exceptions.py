from enum import Enum


class BrantaPaymentExceptionReason(Enum):
    Tampered = "tampered"


class BrantaPaymentException(Exception):
    def __init__(self, message: str, reason: "BrantaPaymentExceptionReason | None" = None) -> None:
        super().__init__(message)
        self.reason = reason


class QRParseException(Exception):
    pass
