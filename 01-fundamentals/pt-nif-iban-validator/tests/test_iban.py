import random
import string

import pytest

from ptvalidators import iban

rng = random.Random(97)

ECBS_EXAMPLE = "GB82 WEST 1234 5698 7654 32"


def as_number(text: str) -> int:
    """Letters to numbers (A=10 ... Z=35) and one big integer, the textbook way."""
    return int("".join(str(int(c, 36)) for c in text))


def make_nib() -> str:
    first19 = "".join(rng.choice(string.digits) for _ in range(19))
    return first19 + f"{98 - int(first19) * 100 % 97:02d}"


def make_iban(country: str) -> str:
    length = iban.LENGTHS[country] - 4
    if country == "PT":
        bban = make_nib()
    else:
        bban = "".join(rng.choice(string.digits) for _ in range(length))
    check = 98 - as_number(bban + country + "00") % 97
    return f"{country}{check:02d}{bban}"


def test_ecbs_example():
    result = iban.validate(ECBS_EXAMPLE)
    assert result.valid
    assert (result.iban, result.country) == ("GB82WEST12345698765432", "GB")


def test_normalisation_and_pretty_format():
    assert iban.is_valid("gb82west12345698765432")
    assert iban.is_valid("IBAN GB82 WEST 1234 5698 7654 32")
    assert iban.pretty("gb82west12345698765432") == ECBS_EXAMPLE


def test_wrong_check_digits_report_the_expected_ones():
    result = iban.validate("GB00 WEST 1234 5698 7654 32")
    assert not result.valid
    assert result.error == "wrong check digits (expected 82)"


@pytest.mark.parametrize("country", sorted(iban.LENGTHS))
def test_generated_ibans_for_every_country(country):
    for _ in range(10):
        value = make_iban(country)
        assert iban.validate(value).valid, value
        assert iban.check_digits(country, value[4:]) == value[2:4]


def test_single_digit_errors_and_swaps_are_caught():
    value = make_iban("DE")
    for i in range(4, len(value)):
        for digit in string.digits:
            if digit != value[i]:
                assert not iban.is_valid(value[:i] + digit + value[i + 1:])
        if i + 1 < len(value) and value[i] != value[i + 1]:
            swapped = value[:i] + value[i + 1] + value[i] + value[i + 2:]
            assert not iban.is_valid(swapped)


def test_mod97_matches_big_integer_arithmetic():
    for _ in range(200):
        text = "".join(rng.choice(string.digits + string.ascii_uppercase) for _ in range(30))
        assert iban.mod97(text) == as_number(text) % 97


def test_portuguese_ibans_always_have_check_digits_50():
    # The NIB is already 1 mod 97, which fixes the IBAN check digits.
    for _ in range(100):
        assert make_iban("PT")[2:4] == "50"


def test_portuguese_nib_check_digits():
    nib = make_nib()
    assert iban.nib_is_valid(nib)
    broken = nib[:19] + f"{(int(nib[19:]) + 1) % 100:02d}"
    assert not iban.nib_is_valid(broken)

    # Recompute the IBAN digits so only the NIB check fails.
    value = "PT" + iban.check_digits("PT", broken) + broken
    result = iban.validate(value)
    assert not result.valid
    assert "NIB" in result.error


@pytest.mark.parametrize("value, error", [
    ("PT50 1234", "PT IBANs have 25 characters, got 8"),
    ("XX12 3456 7890", "country XX is not supported"),
    ("12GB WEST", "must start with a country code and two digits"),
    ("GB82-WEST-1234", "must contain only letters and digits"),
    ("", "must contain only letters and digits"),
])
def test_invalid_input(value, error):
    result = iban.validate(value)
    assert not result.valid
    assert result.error == error
