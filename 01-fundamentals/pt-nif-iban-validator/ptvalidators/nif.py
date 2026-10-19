"""Portuguese tax identification number (NIF / NIPC).

A NIF has 9 digits. The last one is a mod-11 check digit over the first 8 with
weights 9, 8, ..., 2. The first digit (or first two) tells what kind of entity
the number belongs to.
"""

from dataclasses import dataclass

# Longest prefix wins, so "45" is checked before "4" (which on its own is invalid).
PREFIXES = {
    "1": "individual",
    "2": "individual",
    "3": "individual",
    "45": "individual, non-resident",
    "5": "company",
    "6": "public body",
    "70": "undivided inheritance",
    "71": "non-resident company (withholding tax)",
    "72": "investment fund",
    "74": "undivided inheritance",
    "75": "undivided inheritance",
    "77": "assigned by the tax authority",
    "78": "non-resident (VAT refund)",
    "79": "exceptional regime (Expo 98)",
    "8": "sole trader (no longer assigned)",
    "90": "condominium or irregular company",
    "91": "condominium or irregular company",
    "98": "non-resident without permanent establishment",
    "99": "civil partnership without legal personality",
}


@dataclass
class NifResult:
    nif: str
    valid: bool
    entity: str = ""
    error: str = ""


def normalize(value: str) -> str:
    """Drop spaces, dots and an optional 'PT' prefix (as written on invoices)."""
    value = "".join(value.split()).replace(".", "").upper()
    return value[2:] if value.startswith("PT") else value


def check_digit(first8: str) -> int:
    total = sum(int(d) * w for d, w in zip(first8, range(9, 1, -1)))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def entity_type(nif: str) -> str | None:
    return PREFIXES.get(nif[:2]) or PREFIXES.get(nif[:1])


def validate(value: str) -> NifResult:
    nif = normalize(value)
    if not nif.isdigit() or len(nif) != 9:
        return NifResult(nif, False, error="must be exactly 9 digits")
    entity = entity_type(nif)
    if entity is None:
        return NifResult(nif, False, error=f"unknown prefix {nif[:2]}")
    expected = check_digit(nif[:8])
    if int(nif[8]) != expected:
        return NifResult(nif, False, entity, f"wrong check digit (expected {expected})")
    return NifResult(nif, True, entity)


def is_valid(value: str) -> bool:
    return validate(value).valid
