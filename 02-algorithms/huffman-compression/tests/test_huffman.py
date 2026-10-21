import os
import random
from collections import Counter
from pathlib import Path

import pytest

from huffman import (average_length, build_codes, build_tree, compress, decompress, entropy,
                     read_header)

EXAMPLES = Path(__file__).parent.parent / "examples"


def codes_for(data: bytes) -> dict:
    return build_codes(build_tree(Counter(data)))


@pytest.mark.parametrize("data", [
    b"",
    b"a",
    b"aaaaaaaaaaaaaaaaaaaaa",
    b"ab",
    b"abracadabra",
    bytes(range(256)),
    bytes(range(256)) * 3 + b"\x00" * 1000,
], ids=["empty", "one-byte", "single-symbol", "two-symbols", "abracadabra", "all-bytes",
        "skewed"])
def test_round_trip_edge_cases(data):
    assert decompress(compress(data)) == data


def test_round_trip_random_bytes():
    rng = random.Random(0)
    for size in (1, 7, 8, 9, 1000, 50_000):
        data = rng.randbytes(size)
        assert decompress(compress(data)) == data


def test_round_trip_example_texts():
    for name in ("english.txt", "access.log"):
        data = (EXAMPLES / name).read_bytes()
        blob = compress(data)
        assert decompress(blob) == data
        assert len(blob) < len(data)


def test_codes_are_prefix_free():
    rng = random.Random(1)
    for _ in range(50):
        data = bytes(rng.choices(range(40), weights=[rng.random() for _ in range(40)], k=500))
        codes = sorted(codes_for(data).values())
        # after sorting, a code that is a prefix of another comes right before one it prefixes
        for a, b in zip(codes, codes[1:]):
            assert not b.startswith(a)


def test_average_length_between_entropy_and_entropy_plus_one():
    rng = random.Random(2)
    samples = [(EXAMPLES / "english.txt").read_bytes(), (EXAMPLES / "access.log").read_bytes()]
    samples += [bytes(rng.choices(range(10), weights=range(1, 11), k=2000)) for _ in range(20)]
    for data in samples:
        freqs = Counter(data)
        avg = average_length(freqs, build_codes(build_tree(freqs)))
        h = entropy(freqs)
        assert h - 1e-9 <= avg < h + 1


def test_textbook_example_is_optimal():
    # Frequencies from the classic CLRS example: optimal cost is 224 bits.
    freqs = {ord("a"): 45, ord("b"): 13, ord("c"): 12, ord("d"): 16, ord("e"): 9, ord("f"): 5}
    codes = build_codes(build_tree(freqs))
    assert sum(freqs[s] * len(codes[s]) for s in freqs) == 224
    assert len(codes[ord("a")]) == 1


def test_single_symbol_gets_one_bit():
    assert codes_for(b"zzzz") == {ord("z"): "0"}
    assert len(compress(b"z" * 800)) == 4 + 2 + 5 + 1 + 100


def test_header_and_padding():
    blob = compress(b"abracadabra")
    freqs, padding, offset = read_header(blob)
    assert freqs == dict(Counter(b"abracadabra"))
    payload_bits = (len(blob) - offset) * 8 - padding
    codes = codes_for(b"abracadabra")
    assert payload_bits == sum(len(codes[b]) for b in b"abracadabra")
    assert 0 <= padding < 8


def test_compression_is_deterministic():
    data = os.urandom(5000)
    assert compress(data) == compress(data)


def test_random_data_does_not_shrink():
    data = random.Random(3).randbytes(20_000)
    assert len(compress(data)) >= len(data)
    assert entropy(Counter(data)) > 7.9


def test_rejects_foreign_or_corrupted_input():
    with pytest.raises(ValueError):
        decompress(b"PK\x03\x04 not ours")
    blob = compress(b"hello world")
    with pytest.raises(ValueError):
        decompress(blob[:-1])
    with pytest.raises(ValueError):
        decompress(blob[:8])
