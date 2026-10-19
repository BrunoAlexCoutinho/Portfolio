import csv
import hashlib
import json
import os

import pytest

from dupfind import (collect_files, find_duplicates, hash_file, parse_size, wasted_space,
                     write_report)


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


@pytest.fixture
def tree(tmp_path):
    big = os.urandom(100_000)
    write(tmp_path / "a" / "photo.jpg", big)
    write(tmp_path / "b" / "photo copy.jpg", big)
    write(tmp_path / "b" / "deep" / "photo.jpg", big)
    write(tmp_path / "a" / "same-size-1.bin", os.urandom(5000))
    write(tmp_path / "a" / "same-size-2.bin", os.urandom(5000))
    header = os.urandom(4096)
    write(tmp_path / "a" / "log1.txt", header + b"ending one")
    write(tmp_path / "a" / "log2.txt", header + b"ending two")
    write(tmp_path / "a" / "unique.txt", b"only me")
    write(tmp_path / "a" / "empty1", b"")
    write(tmp_path / "b" / "empty2", b"")
    return tmp_path


def test_parse_size():
    assert parse_size("500") == 500
    assert parse_size("10K") == 10 * 1024
    assert parse_size("2mb") == 2 * 1024 ** 2
    assert parse_size("1.5G") == int(1.5 * 1024 ** 3)


def test_hash_file_full_and_prefix(tmp_path):
    data = os.urandom(200_000)  # several read chunks
    f = write(tmp_path / "f", data)
    assert hash_file(f) == hashlib.sha256(data).hexdigest()
    assert hash_file(f, 4096) == hashlib.sha256(data[:4096]).hexdigest()


def test_finds_exact_duplicates_only(tree):
    duplicates, _ = find_duplicates(collect_files([tree]))
    assert len(duplicates) == 1
    names = sorted(os.path.basename(p) for p in duplicates[0]["paths"])
    assert names == ["photo copy.jpg", "photo.jpg", "photo.jpg"]
    assert duplicates[0]["size"] == 100_000


def test_each_stage_eliminates_its_kind_of_false_candidate(tree):
    _, stats = find_duplicates(collect_files([tree]))
    size, prefix, full = stats
    assert (size["before"], size["after"]) == (8, 7)      # unique.txt has a unique size
    assert (prefix["before"], prefix["after"]) == (7, 5)  # same-size-*.bin differ early
    assert (full["before"], full["after"]) == (5, 3)      # log*.txt differ only at the end


def test_empty_files_ignored_by_default_but_can_be_included(tree):
    files = collect_files([tree], min_size=0)
    duplicates, _ = find_duplicates(files)
    assert any(d["size"] == 0 for d in duplicates)
    assert len(collect_files([tree])) == 8


def test_min_size_and_exclude(tree):
    assert all(size >= 6000 for _, size in collect_files([tree], min_size=6000))
    files = collect_files([tree], exclude=["b/*"])
    assert not any("photo copy" in str(p) for p, _ in files)
    files = collect_files([tree], exclude=["*.txt"])
    assert not any(str(p).endswith(".txt") for p, _ in files)


def test_overlapping_roots_count_files_once(tree):
    files = collect_files([tree, tree / "a"])
    assert len(files) == len({p.resolve() for p, _ in files})
    duplicates, _ = find_duplicates(files)
    assert len(duplicates[0]["paths"]) == 3


def test_hard_link_is_not_a_duplicate(tmp_path):
    original = write(tmp_path / "x.bin", os.urandom(1000))
    os.link(original, tmp_path / "x-link.bin")
    duplicates, _ = find_duplicates(collect_files([tmp_path]))
    assert duplicates == []


def test_wasted_space():
    groups = [{"size": 100, "paths": ["a", "b", "c"]}, {"size": 10, "paths": ["d", "e"]}]
    assert wasted_space(groups) == 210


def test_reports(tree, tmp_path):
    duplicates, _ = find_duplicates(collect_files([tree]))
    write_report(tmp_path / "r.json", duplicates)
    assert json.loads((tmp_path / "r.json").read_text()) == duplicates

    write_report(tmp_path / "r.csv", duplicates)
    with open(tmp_path / "r.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3 and {r["group"] for r in rows} == {"1"}


def test_finder_never_modifies_files(tree):
    before = {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()}
    find_duplicates(collect_files([tree]))
    assert {p: p.read_bytes() for p in tree.rglob("*") if p.is_file()} == before
