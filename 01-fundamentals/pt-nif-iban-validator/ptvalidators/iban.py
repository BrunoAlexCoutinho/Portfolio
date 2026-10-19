"""IBAN validation (ISO 13616, mod-97 check from ISO 7064).

For Portuguese IBANs the embedded NIB has its own two check digits, which are
checked as well.
"""

from dataclasses import dataclass

# IBAN length per country: EU and EEA members, plus Switzerland and the UK.
LENGTHS = {
    "AT": 20, "BE": 16, "BG": 22, "CH": 21, "CY": 28, "CZ": 24, "DE": 22, "DK": 18,
    "EE": 20, "ES": 24, "FI": 18, "FR": 27, "GB": 22, "GR": 27, "HR": 21, "HU": 28,
    "IE": 22, "IS": 26, "IT": 27, "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MT": 31,
    "NL": 18, "NO": 15, "PL": 28, "PT": 25, "RO": 24, "SE": 24, "SI": 19, "SK": 24,
}


@dataclass
class IbanResult:
    iban: str
    valid: bool
    country: str = ""
    error: str = ""


def normalize(value: str) -> str:
    """Remove whitespace and an optional 'IBAN' label; uppercase."""
    value = "".join(value.split()).upper()
    return value[4:] if value.startswith("IBAN") else value


def pretty(iban: str) -> str:
    """Print format: groups of four characters."""
    iban = normalize(iban)
    return " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))


def mod97(text: str) -> int:
    """Remainder of the number formed by `text` (A=10 ... Z=35) divided by 97.

    Works digit by digit, the way it is done in languages without big integers.
    """
    remainder = 0
    for char in text:
        value = int(char, 36)                    # '0'-'9' -> 0-9, 'A'-'Z' -> 10-35
        remainder = (remainder * (100 if value > 9 else 10) + value) % 97
    return remainder


def check_digits(country: str, bban: str) -> str:
    """The two IBAN check digits for a country code and BBAN."""
    return f"{98 - mod97(bban + country + '00'):02d}"


def nib_is_valid(nib: str) -> bool:
    """Portuguese NIB: bank (4) + branch (4) + account (11) + check (2).

    The check digits are 98 - (first 19 digits * 100 mod 97), which is the
    same as saying the whole 21-digit number is 1 mod 97.
    """
    return len(nib) == 21 and nib.isdigit() and mod97(nib) == 1


def validate(value: str) -> IbanResult:
    iban = normalize(value)
    if len(iban) < 5 or not iban.isalnum() or not iban.isascii():
        return IbanResult(iban, False, error="must contain only letters and digits")
    country, digits, bban = iban[:2], iban[2:4], iban[4:]
    if not country.isalpha() or not digits.isdigit():
        return IbanResult(iban, False, error="must start with a country code and two digits")
    if country not in LENGTHS:
        return IbanResult(iban, False, country, f"country {country} is not supported")
    if len(iban) != LENGTHS[country]:
        return IbanResult(iban, False, country,
                          f"{country} IBANs have {LENGTHS[country]} characters, got {len(iban)}")
    if mod97(bban + country + digits) != 1:
        return IbanResult(iban, False, country,
                          f"wrong check digits (expected {check_digits(country, bban)})")
    if country == "PT" and not nib_is_valid(bban):
        return IbanResult(iban, False, country,
                          "IBAN checksum is fine but the NIB check digits are wrong")
    return IbanResult(iban, True, country)


def is_valid(value: str) -> bool:
    return validate(value).valid
