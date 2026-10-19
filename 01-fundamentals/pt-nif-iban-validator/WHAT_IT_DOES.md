# pt-nif-iban-validator — What it does

## In one sentence
An installable Python package and command-line tool (`ptvalidate`) that checks whether Portuguese tax numbers (NIF) and IBANs are correctly formed by verifying their built-in check digits, and explains why a value is invalid.

## The problem it solves
Supplier records, invoices and forms in Portugal almost always carry a NIF and an IBAN, and typing mistakes are common. Both numbers contain check digits, so most typos (a wrong digit, two swapped digits) can be detected before the data is saved or a bank transfer fails. This tool runs those checks offline, one value at a time or for a whole list, and can also be imported from other Python code.

## Input
- A kind: `nif` or `iban`.
- One or more values on the command line (quote values that contain spaces), and/or `-f FILE` / `--file FILE`: a text file with one value per line. Blank lines and lines starting with `#` are ignored.
- Accepted NIF formats: `123456789`, `123 456 789`, `123.456.789`, `PT 123 456 789` (spaces and dots removed, optional `PT` prefix dropped).
- Accepted IBAN formats: with or without spaces, upper or lower case, optional leading `IBAN` label.
- From Python: `nif.validate(text)`, `iban.validate(text)`, `nif.is_valid`, `iban.is_valid`, `iban.pretty`.

## How it works
1. **Read the values** (`ptvalidators/__main__.py`): `main` collects values from the arguments plus `read_values` for `--file`. If there are none, or the file cannot be opened, it prints an error and exits with code 2.
2. **NIF check** (`ptvalidators/nif.py`, `validate`):
   - `normalize` removes whitespace and dots, uppercases, and strips a leading `PT`.
   - The result must be exactly 9 digits, otherwise "must be exactly 9 digits".
   - `entity_type` looks up the prefix in the `PREFIXES` table, two-digit prefix first, then one-digit (e.g. `1`/`2`/`3` individual, `45` non-resident individual, `5` company, `6` public body, `72` investment fund, `98` non-resident without permanent establishment, `99` civil partnership). An unknown prefix (such as `4` alone or `73`) is rejected with "unknown prefix".
   - `check_digit` multiplies the first 8 digits by weights 9, 8, ..., 2, sums them, takes `r = sum mod 11`; the expected 9th digit is `0` if `r` is 0 or 1, otherwise `11 - r`. A mismatch gives "wrong check digit (expected N)".
3. **IBAN check** (`ptvalidators/iban.py`, `validate`):
   - `normalize` removes whitespace, uppercases and strips an `IBAN` label.
   - It must be ASCII letters and digits, at least 5 characters, starting with two letters (country) and two digits (check digits).
   - The country must be in the `LENGTHS` table (32 countries: EU/EEA members plus Switzerland and the UK) and the total length must match that country (e.g. PT = 25, DE = 22, GB = 22).
   - ISO 13616 / ISO 7064 mod-97 check: the country code and check digits are moved to the end, letters become numbers (A = 10 ... Z = 35), and the resulting number must leave remainder 1 when divided by 97. `mod97` does this one character at a time, keeping only the remainder. On failure, `check_digits` computes the correct digits (`98 - mod97(BBAN + country + "00")`) and the error says which ones were expected.
   - For Portuguese IBANs only, `nib_is_valid` also checks the embedded 21-digit NIB (bank 4 + branch 4 + account 11 + check 2): it must itself be 1 mod 97. This catches cases where the IBAN check digits were recomputed after the account number was altered.
4. **Print results** (`check_nifs` / `check_ibans`): one line per value, `VALID` with the entity type (NIF) or country (IBAN), or `INVALID` with the reason. IBANs are shown in groups of four with `pretty`. A summary line is added when more than one value was checked.

## Output
Console lines, one per value, plus a summary for lists. Exit codes: `0` = all valid, `1` = at least one invalid, `2` = no input or file not readable. From Python, `validate` returns a `NifResult(nif, valid, entity, error)` or `IbanResult(iban, valid, country, error)`.

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

$ ptvalidate iban "PT71 1234 5678 1234 5678 9010 0"
INVALID  PT71 1234 5678 1234 5678 9010 0         IBAN checksum is fine but the NIB check digits are wrong
```

## Files
- `ptvalidators/nif.py` — NIF normalisation, mod-11 check digit, prefix-to-entity table, `validate` / `is_valid`.
- `ptvalidators/iban.py` — IBAN normalisation, country length table, digit-by-digit mod-97, expected check digits, Portuguese NIB check, `pretty` formatting, `validate` / `is_valid`.
- `ptvalidators/__main__.py` — command-line interface (`python -m ptvalidators` or `ptvalidate`), file reading, result printing and exit codes.
- `ptvalidators/__init__.py` — exposes the `nif` and `iban` modules and the version (`0.1.0`).
- `pyproject.toml` — package metadata; registers the `ptvalidate` console command for `pip install -e .`.
- `examples/nifs.txt`, `examples/ibans.txt` — synthetic and documentation sample values, valid and invalid.
- `tests/test_nif.py`, `tests/test_iban.py`, `tests/test_cli.py` — pytest tests (valid numbers generated in the tests, typo detection, CLI exit codes).
- `HOW_TO_RUN.txt`, `README.md` — usage instructions and documentation.

## What it does not do
- It does not check that a NIF or IBAN actually exists or belongs to anyone; it only checks that the number is well formed. No online lookup is made.
- It does not validate the per-country internal structure of non-Portuguese IBANs (which positions must be letters or digits); only length and the mod-97 check.
- IBANs from countries outside its 32-country table are rejected as "not supported".
- It does not map Portuguese bank codes to bank names, nor validate VAT numbers of other countries.
