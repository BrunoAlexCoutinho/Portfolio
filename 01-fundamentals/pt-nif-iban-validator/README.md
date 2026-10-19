# pt-nif-iban-validator

A small installable Python package that validates Portuguese tax numbers (NIF) and IBANs, with a command-line tool.

## Purpose

Forms, invoices and supplier records in Portugal almost always carry a NIF and an IBAN, and typos in either are common. Both numbers have built-in check digits, so most mistakes can be caught before anything is saved or a transfer fails. This project implements those checks without dependencies and packages them properly: `pyproject.toml`, a console script, tests and CI.

## Features

- **NIF**: 9 digits, mod-11 check digit, and the entity type given by the prefix (individual, company, public body, investment fund, undivided inheritance, ...)
- **IBAN**: ISO 13616 mod-97 check, length table for EU/EEA countries plus Switzerland and the UK, accepts spaces and lowercase, prints in groups of four
- **Portuguese IBANs**: the NIB inside the IBAN has its own two check digits, which are verified too
- Errors say what is wrong: "wrong check digit (expected 9)", "PT IBANs have 25 characters, got 24"
- CLI: `ptvalidate nif ...`, `ptvalidate iban ...`, `--file` for lists; exit code 1 if anything is invalid
- Installable with `pip install -e .`

## Technologies

- Python 3.10+ (standard library only)
- setuptools (`pyproject.toml`), pytest, GitHub Actions

## Installation

```bash
git clone <repo-url>
cd pt-nif-iban-validator
pip install -e .            # installs the package and the ptvalidate command
```

## Usage

```bash
ptvalidate nif 123456789
ptvalidate nif "PT 501 234 560" 600000001
ptvalidate iban "GB82 WEST 1234 5698 7654 32"
ptvalidate nif --file examples/nifs.txt
ptvalidate iban --file examples/ibans.txt

python -m ptvalidators nif 123456789          # same thing without installing
```

From Python:

```python
>>> from ptvalidators import nif, iban
>>> nif.validate("PT 501 234 560")
NifResult(nif='501234560', valid=True, entity='company', error='')
>>> iban.validate("pt50 1234 5678 1234 5678 9018 7")
IbanResult(iban='PT50123456781234567890187', valid=True, country='PT', error='')
>>> iban.pretty("PT50123456781234567890187")
'PT50 1234 5678 1234 5678 9018 7'
```

Exit codes: `0` all valid, `1` at least one invalid value, `2` no input or unreadable file.

## Example

The sample files contain only synthetic numbers and the documented example IBANs (ECBS `GB82 WEST ...`, the common `DE89 3704 ...` example).

```text
$ ptvalidate nif --file examples/nifs.txt
VALID    123456789  individual
VALID    501234560  company
VALID    600000001  public body
VALID    980000009  non-resident without permanent establishment
VALID    450000001  individual, non-resident
INVALID  123456780  wrong check digit (expected 9)
INVALID  730000000  unknown prefix 73
INVALID  12345678   must be exactly 9 digits

8 checked, 5 valid, 3 invalid

$ ptvalidate iban --file examples/ibans.txt
VALID    GB82 WEST 1234 5698 7654 32             GB
VALID    DE89 3704 0044 0532 0130 00             DE
VALID    PT50 1234 5678 1234 5678 9018 7         PT
VALID    PT50 0001 0000 0000 0000 0015 7         PT
INVALID  GB82 WEST 1234 5698 7654 23             wrong check digits (expected 34)
INVALID  PT50 1234 5678 1234 5678 9018           PT IBANs have 25 characters, got 24
INVALID  PT71 1234 5678 1234 5678 9010 0         IBAN checksum is fine but the NIB check digits are wrong

7 checked, 4 valid, 3 invalid
```

The last line is a Portuguese IBAN whose IBAN check digits were recomputed after the NIB was altered. The generic mod-97 check passes; only the NIB check catches it.

## How the checks work

**NIF.** Multiply the first 8 digits by 9, 8, ..., 2 and add them up. With `r = sum % 11`, the check digit is `0` if `r` is 0 or 1, otherwise `11 - r`. Example: `12345678` gives 156, `156 % 11 = 2`, so the 9th digit is `9`.

| Prefix | Entity |
|--------|--------|
| 1, 2, 3 | individual |
| 45 | non-resident individual |
| 5 | company |
| 6 | public body |
| 70, 74, 75 | undivided inheritance |
| 71 | non-resident company (withholding tax) |
| 72 | investment fund |
| 77 | assigned by the tax authority |
| 78 | non-resident (VAT refund) |
| 79 | exceptional regime (Expo 98) |
| 8 | sole trader (no longer assigned) |
| 90, 91 | condominium or irregular company |
| 98 | non-resident without permanent establishment |
| 99 | civil partnership without legal personality |

**IBAN.** Move the country code and check digits to the end, replace letters with numbers (A = 10, ..., Z = 35) and the result must be `1 mod 97`. The number has up to ~60 digits, so `mod97()` processes it one character at a time and keeps only the remainder.

**NIB (PT).** A Portuguese BBAN is the 21-digit NIB: bank (4), branch (4), account (11), check (2). The NIB check digits are chosen so that the NIB on its own is `1 mod 97`. A side effect: every valid Portuguese IBAN starts with `PT50`. The tests check this on 100 generated IBANs.

## Project Structure

```text
ptvalidators/__init__.py    package version, exposes nif and iban
ptvalidators/nif.py         NIF normalisation, check digit, prefix table
ptvalidators/iban.py        IBAN normalisation, mod-97, length table, NIB check, pretty print
ptvalidators/__main__.py    CLI (python -m ptvalidators / ptvalidate)
pyproject.toml              setuptools metadata and the console script
examples/                   nifs.txt and ibans.txt with valid and invalid samples
tests/                      pytest tests; valid numbers are generated inside the tests
.github/workflows/tests.yml installs the package and runs the tests on every push
```

## What I Learned

- A check digit catches every single-digit typo and every swap of two adjacent digits in an IBAN, which the tests verify exhaustively for a generated number.
- Computing mod 97 piece by piece avoids big integers; Python doesn't need it, but it is how the check is done in most other languages.
- Why every Portuguese IBAN starts with `PT50`: the NIB is already `1 mod 97`, so the IBAN check digits always come out the same.
- With `pyproject.toml` and `[project.scripts]`, one `pip install -e .` gives an importable package and a command on the PATH.

## Possible Improvements

- Check the BBAN structure per country (letters vs digits in each position), not only the length
- Map Portuguese bank codes to bank names
- Validate VAT numbers of other EU countries (the PT NIF is the PT VAT number)
- Publish to PyPI with a version tag workflow
