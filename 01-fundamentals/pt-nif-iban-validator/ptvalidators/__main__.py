"""Command line: python -m ptvalidators nif 123456789  /  ptvalidate iban "PT50 ..." """

import argparse
import sys

from . import iban, nif


def read_values(path: str) -> list[str]:
    """One value per line; blank lines and lines starting with # are skipped."""
    with open(path, encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


def check_nifs(values) -> int:
    invalid = 0
    for value in values:
        result = nif.validate(value)
        if result.valid:
            print(f"VALID    {result.nif:<11}{result.entity}")
        else:
            invalid += 1
            print(f"INVALID  {result.nif or '(empty)':<11}{result.error}")
    return invalid


def check_ibans(values) -> int:
    invalid = 0
    for value in values:
        result = iban.validate(value)
        if result.valid:
            print(f"VALID    {iban.pretty(result.iban):<40}{result.country}")
        else:
            invalid += 1
            print(f"INVALID  {iban.pretty(result.iban) or '(empty)':<40}{result.error}")
    return invalid


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ptvalidate", description="Validate Portuguese NIF numbers and IBANs.")
    sub = parser.add_subparsers(dest="kind", required=True)
    for kind, help_text in (("nif", "Portuguese tax number (9 digits)"),
                            ("iban", "IBAN, with or without spaces")):
        p = sub.add_parser(kind, help=help_text)
        p.add_argument("values", nargs="*", help="values to check; quote values that contain spaces")
        p.add_argument("-f", "--file", help="file with one value per line")
    args = parser.parse_args(argv)

    values = list(args.values)
    if args.file:
        try:
            values += read_values(args.file)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
    if not values:
        print("error: give at least one value or --file", file=sys.stderr)
        return 2

    check = check_nifs if args.kind == "nif" else check_ibans
    invalid = check(values)
    if len(values) > 1:
        print(f"\n{len(values)} checked, {len(values) - invalid} valid, {invalid} invalid")
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
