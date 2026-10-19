from ptvalidators.__main__ import main


def test_all_valid_returns_0(capsys):
    assert main(["iban", "GB82 WEST 1234 5698 7654 32"]) == 0
    assert capsys.readouterr().out.startswith("VALID    GB82 WEST 1234 5698 7654 32")


def test_any_invalid_returns_1(capsys):
    assert main(["nif", "123456789", "123456780"]) == 1
    out = capsys.readouterr().out
    assert "INVALID  123456780  wrong check digit (expected 9)" in out
    assert "2 checked, 1 valid, 1 invalid" in out


def test_file_input_skips_comments_and_blank_lines(tmp_path, capsys):
    path = tmp_path / "nifs.txt"
    path.write_text("# header\n123456789\n\nPT 123 456 789\n", encoding="utf-8")
    assert main(["nif", "--file", str(path)]) == 0
    assert "2 checked, 2 valid, 0 invalid" in capsys.readouterr().out


def test_bad_input_returns_2(tmp_path, capsys):
    assert main(["nif"]) == 2
    assert main(["iban", "--file", str(tmp_path / "missing.txt")]) == 2
