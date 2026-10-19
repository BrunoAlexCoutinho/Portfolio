import random

import pytest

from ptvalidators import nif

rng = random.Random(2026)


def make_nif(prefix: str) -> str:
    """Build a synthetic valid NIF: prefix + random digits + mod-11 check digit."""
    body = prefix + "".join(rng.choice("0123456789") for _ in range(8 - len(prefix)))
    total = sum(int(d) * (9 - i) for i, d in enumerate(body))
    check = 11 - total % 11
    return body + ("0" if check >= 10 else str(check))


@pytest.mark.parametrize("prefix", sorted(nif.PREFIXES))
def test_generated_numbers_are_valid_for_every_prefix(prefix):
    for _ in range(20):
        number = make_nif(prefix)
        result = nif.validate(number)
        assert result.valid, number
        assert result.entity == nif.PREFIXES[prefix]


def test_any_other_check_digit_is_rejected():
    for _ in range(50):
        number = make_nif(rng.choice(["1", "2", "5", "6"]))
        for digit in "0123456789":
            if digit != number[8]:
                result = nif.validate(number[:8] + digit)
                assert not result.valid
                assert result.error == f"wrong check digit (expected {number[8]})"


def test_check_digit_examples():
    assert nif.check_digit("12345678") == 9     # 156 % 11 == 2 -> 11 - 2
    assert nif.check_digit("20000002") == 0     # 22 % 11 == 0 -> 0
    assert nif.check_digit("50000000") == 0     # 45 % 11 == 1 -> 0 as well


def test_entity_types():
    assert nif.entity_type("512345678") == "company"
    assert nif.entity_type("612345678") == "public body"
    assert nif.entity_type("452345678") == "individual, non-resident"
    assert nif.entity_type("992345678") == "civil partnership without legal personality"


@pytest.mark.parametrize("prefix", ["0", "40", "73", "76", "92", "97"])
def test_unknown_prefixes(prefix):
    number = make_nif(prefix)      # correct check digit, impossible prefix
    result = nif.validate(number)
    assert not result.valid
    assert result.error.startswith("unknown prefix")


@pytest.mark.parametrize("value", ["", "12345678", "1234567890", "12345678A", "-12345678"])
def test_wrong_format(value):
    assert nif.validate(value).error == "must be exactly 9 digits"


def test_normalisation():
    number = make_nif("5")
    spaced = f"PT {number[:3]} {number[3:6]} {number[6:]}"
    dotted = f"{number[:3]}.{number[3:6]}.{number[6:]}"
    assert nif.validate(spaced).nif == number
    assert nif.is_valid(spaced)
    assert nif.is_valid(dotted)
    assert nif.is_valid(" pt" + number + "\n")
