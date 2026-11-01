from enum import Enum


class BrantaEnvironment(str, Enum):
    Staging = "Staging"
    Production = "Production"
    Localhost = "Localhost"


BrantaEnvironmentUrls = {
    BrantaEnvironment.Staging: "https://staging.guardrail.branta.pro",
    BrantaEnvironment.Production: "https://guardrail.branta.pro",
    BrantaEnvironment.Localhost: "http://localhost:3000",
}


class DestinationType(str, Enum):
    BitcoinAddress = "bitcoin_address"
    Bolt11 = "bolt11"
    ArkAddress = "ark_address"
    SilentPayment = "silent_payment"


class VerifyStatus(str, Enum):
    Match = "match"
    Unknown = "unknown"
    Tampered = "tampered"
    Incomplete = "incomplete"
