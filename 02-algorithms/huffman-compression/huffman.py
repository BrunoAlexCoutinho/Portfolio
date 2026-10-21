"""Huffman coding of bytes: compress, decompress and compare with the Shannon entropy."""

import argparse
import heapq
import math
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

MAGIC = b"HUF1"


def build_tree(freqs: dict):
    """Huffman tree as nested tuples (left, right); leaves are byte values.

    Heap entries are (weight, order, node). `order` is unique, so ties are
    broken the same way every time and nodes are never compared. The
    decoder rebuilds the identical tree from the same frequency table.
    """
    heap = [(weight, symbol, symbol) for symbol, weight in sorted(freqs.items())]
    heapq.heapify(heap)
    order = 256
    while len(heap) > 1:
        w1, _, left = heapq.heappop(heap)
        w2, _, right = heapq.heappop(heap)
        heapq.heappush(heap, (w1 + w2, order, (left, right)))
        order += 1
    return heap[0][2] if heap else None


def build_codes(tree) -> dict:
    """Map each byte value to its code as a '0'/'1' string."""
    if tree is None:
        return {}
    if isinstance(tree, int):
        return {tree: "0"}       # one distinct symbol still needs one bit per symbol
    codes = {}
    stack = [(tree, "")]
    while stack:
        node, prefix = stack.pop()
        if isinstance(node, int):
            codes[node] = prefix
        else:
            stack.append((node[0], prefix + "0"))
            stack.append((node[1], prefix + "1"))
    return codes


def compress(data: bytes) -> bytes:
    """Header (magic, frequency table, padding bits) followed by the packed codes."""
    freqs = Counter(data)
    codes = build_codes(build_tree(freqs))
    table = {s: (int(c, 2), len(c)) for s, c in codes.items()}

    out = bytearray()
    acc = nbits = 0
    for byte in data:
        value, length = table[byte]
        acc = (acc << length) | value
        nbits += length
        while nbits >= 8:
            nbits -= 8
            out.append((acc >> nbits) & 0xFF)
        acc &= (1 << nbits) - 1
    padding = (8 - nbits) % 8
    if nbits:
        out.append((acc << padding) & 0xFF)

    header = bytearray(MAGIC)
    header += struct.pack(">H", len(freqs))
    for symbol in sorted(freqs):
        header += struct.pack(">BI", symbol, freqs[symbol])
    header.append(padding)
    return bytes(header + out)


def read_header(blob: bytes) -> tuple[dict, int, int]:
    """Returns (frequency table, padding bits, offset of the payload)."""
    if blob[:4] != MAGIC or len(blob) < 7:
        raise ValueError("not a file written by this compressor")
    (count,) = struct.unpack_from(">H", blob, 4)
    offset = 6
    freqs = {}
    for _ in range(count):
        symbol, weight = struct.unpack_from(">BI", blob, offset)
        freqs[symbol] = weight
        offset += 5
    if offset >= len(blob):
        raise ValueError("truncated header")
    padding = blob[offset]
    if padding > 7:
        raise ValueError("corrupted header: bad padding")
    return freqs, padding, offset + 1


def decompress(blob: bytes) -> bytes:
    try:
        freqs, padding, offset = read_header(blob)
    except struct.error:
        raise ValueError("truncated header") from None
    tree = build_tree(freqs)
    total = sum(freqs.values())
    if tree is None:
        return b""
    if isinstance(tree, int):
        return bytes([tree]) * total

    out = bytearray()
    node = tree
    payload = blob[offset:]
    nbits = len(payload) * 8 - padding
    for i in range(nbits):
        bit = (payload[i >> 3] >> (7 - (i & 7))) & 1
        node = node[bit]
        if isinstance(node, int):
            out.append(node)
            node = tree
    if len(out) != total:
        raise ValueError(f"corrupted data: decoded {len(out)} of {total} bytes")
    return bytes(out)


def entropy(freqs: dict) -> float:
    """Shannon entropy in bits per symbol: the lower bound for any symbol-by-symbol code."""
    total = sum(freqs.values())
    return sum(f / total * math.log2(total / f) for f in freqs.values() if f)


def average_length(freqs: dict, codes: dict) -> float:
    total = sum(freqs.values())
    return sum(freqs[s] * len(codes[s]) for s in freqs) / total if total else 0.0


def show(symbol: int) -> str:
    char = chr(symbol)
    if char == " ":
        return "' '"
    return repr(char) if char.isprintable() and symbol < 128 else f"0x{symbol:02x}"


def cmd_compress(args) -> int:
    data = args.input.read_bytes()
    blob = compress(data)
    args.output.write_bytes(blob)
    ratio = len(blob) / len(data) if data else 0
    print(f"{args.input} -> {args.output}: {len(data):,} -> {len(blob):,} bytes "
          f"({ratio:.1%} of original)")
    return 0


def cmd_decompress(args) -> int:
    data = decompress(args.input.read_bytes())
    args.output.write_bytes(data)
    print(f"{args.input} -> {args.output}: {len(data):,} bytes restored")
    return 0


def cmd_stats(args) -> int:
    data = args.input.read_bytes()
    freqs = Counter(data)
    codes = build_codes(build_tree(freqs))
    blob = compress(data)
    h = entropy(freqs)
    avg = average_length(freqs, codes)
    header = 7 + 5 * len(freqs)

    print(f"File:              {args.input} ({len(data):,} bytes, {len(freqs)} distinct)")
    print(f"Entropy:           {h:.3f} bits/symbol")
    print(f"Huffman average:   {avg:.3f} bits/symbol  (+{avg - h:.3f} over entropy)")
    print(f"Payload:           {len(blob) - header:,} bytes  "
          f"(entropy bound {math.ceil(h * len(data) / 8):,})")
    print(f"Header:            {header:,} bytes")
    if not data:
        return 0

    deflated = len(zlib.compress(data, 9))
    print(f"Compressed total:  {len(blob):,} bytes = {len(blob) / len(data):.1%} of original "
          f"(ratio {len(data) / len(blob):.2f}:1)")
    print(f"zlib -9 (LZ77 + Huffman), for reference: {deflated:,} bytes "
          f"= {deflated / len(data):.1%}")

    print(f"\nTop {args.top} symbols")
    print(f"  {'symbol':<8}{'count':>8}{'share':>8}  code")
    for symbol, count in freqs.most_common(args.top):
        print(f"  {show(symbol):<8}{count:>8}{count / len(data):>8.1%}  {codes[symbol]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Huffman compression of any file.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, help_text in [("compress", cmd_compress, "compress INPUT into OUTPUT"),
                                  ("decompress", cmd_decompress, "restore a compressed file")]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("input", type=Path)
        p.add_argument("output", type=Path)
        p.set_defaults(func=func)

    p_stats = sub.add_parser("stats", help="entropy, average code length and top codes")
    p_stats.add_argument("input", type=Path)
    p_stats.add_argument("--top", type=int, default=10, help="symbols to list (default 10)")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if hasattr(args, "output") and args.output.resolve() == args.input.resolve():
        print("error: output must be a different file", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
