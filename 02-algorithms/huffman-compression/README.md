# huffman-compression

A Huffman compressor for any file: builds the code with a priority queue, packs the bits into bytes, restores the original exactly, and compares the result with the Shannon entropy of the file.

## Purpose

Huffman coding is the textbook example of a greedy algorithm that is provably optimal, and it is still used inside DEFLATE (zip, gzip, PNG) and JPEG. Implementing the full round trip (frequency table, tree, codes, bit packing, file header, decoding) shows the details the textbook skips: tie-breaking, the last partial byte, files with zero or one distinct symbol. The `stats` command connects it to information theory by comparing the average code length with the entropy bound.

## Features

- `compress` / `decompress` any file (text or binary), byte-exact round trip
- Tree built with `heapq`, with deterministic tie-breaking so the decoder rebuilds the same tree
- File format: magic `HUF1`, frequency table, number of padding bits, packed codes
- Handles empty files and files with a single distinct byte
- `stats`: entropy, Huffman average bits per symbol, payload vs entropy bound, header overhead, compression ratio, zlib for reference, and the most frequent symbols with their codes
- Example files: an English text, a repetitive log file, and a generator for random bytes

## Technologies

- Python 3.10+ (standard library: `heapq`, `collections.Counter`, `struct`, `math`, `zlib` for the reference number only)
- pytest for tests

## Installation

No dependencies. Clone and run.

## Usage

```bash
python huffman.py compress INPUT OUTPUT
python huffman.py decompress INPUT OUTPUT
python huffman.py stats INPUT [--top N]
python examples/make_random.py OUTPUT [--size BYTES] [--seed N]
```

## Example

```text
$ python huffman.py compress examples/english.txt english.huf
examples/english.txt -> english.huf: 4,183 -> 2,659 bytes (63.6% of original)
$ python huffman.py decompress english.huf english.out
english.huf -> english.out: 4,183 bytes restored

$ python huffman.py stats examples/english.txt
File:              examples/english.txt (4,183 bytes, 66 distinct)
Entropy:           4.403 bits/symbol
Huffman average:   4.440 bits/symbol  (+0.037 over entropy)
Payload:           2,322 bytes  (entropy bound 2,303)
Header:            337 bytes
Compressed total:  2,659 bytes = 63.6% of original (ratio 1.57:1)
zlib -9 (LZ77 + Huffman), for reference: 2,047 bytes = 48.9%

Top 10 symbols
  symbol     count   share  code
  ' '          725   17.3%  111
  'e'          407    9.7%  001
  't'          318    7.6%  1011
  'a'          261    6.2%  1010
  'o'          259    6.2%  1001
  's'          255    6.1%  0111
  'n'          217    5.2%  0101
  'i'          194    4.6%  0001
  'r'          181    4.3%  0000
  'h'          163    3.9%  11001
```

The space and `e` get 3-bit codes instead of 8. The average, 4.440 bits, is only 0.037 bits above the entropy, which is the lower bound for any code that maps each byte to a fixed bit string.

The three example files side by side (from `stats`):

| File | Size | Entropy (bits/byte) | Huffman avg | Huffman total | zlib -9 |
|------|-----:|--------------------:|------------:|--------------:|--------:|
| `english.txt` | 4,183 | 4.403 | 4.440 | 63.6% | 48.9% |
| `access.log` | 8,962 | 4.924 | 4.943 | 64.6% | 17.8% |
| `random.bin` (20 KB) | 20,000 | 7.989 | 8.000 | **106.4%** | 100.1% |

- **Random data does not compress.** Its entropy is ~8 bits per byte, so 253 of the 256 codes are exactly 8 bits long (one has 7, two have 9). The payload stays at 20,000 bytes, and the 1,287-byte frequency table makes the output bigger than the input.
- **Huffman only sees single-byte frequencies.** The log file repeats the same timestamps, paths and status codes on every line, but Huffman can't use that: it compresses the log about as well as the English text. zlib first replaces repeated strings with back-references (LZ77) and then applies Huffman codes, and reaches 17.8%.
- **The header matters on small files.** For `english.txt` the table is 337 of 2,659 bytes.

## How it works

1. Count every byte value (`Counter`).
2. Push `(count, order, node)` for each symbol into a heap. Pop the two smallest, push their parent with the summed count, repeat until one node is left. `order` is the byte value for leaves and an increasing counter for internal nodes, so ties always break the same way and the decoder, which reads the same table, builds the same tree.
3. Walk the tree: left = `0`, right = `1`. Every symbol is a leaf, so no code is a prefix of another.
4. Encode by appending each code to an integer bit buffer and emitting a byte every time 8 bits are ready. The last byte is padded with zeros and the number of padding bits goes into the header.
5. Decode by reading bits one by one and walking the tree from the root, emitting a symbol at each leaf. The total from the frequency table is checked at the end to detect truncated files.

Header layout: `HUF1` (4 bytes), number of symbols (2 bytes), then 5 bytes per symbol (byte value + 32-bit count), then 1 byte of padding count.

Special cases: an empty file has no tree and compresses to the 7-byte header. A file with one distinct byte would give a tree that is a single leaf with an empty code, so that symbol gets the code `0` (1 bit per byte).

## Project Structure

```text
huffman.py              tree, codes, bit packing, file format, entropy and CLI
examples/english.txt    about 4 KB of English prose (written for this project)
examples/access.log     synthetic web server log, 140 lines
examples/make_random.py writes N seeded random bytes
tests/                  round trips, prefix property, entropy bound, error handling
```

## Running the tests

```bash
pip install pytest
pytest
```

## What I Learned

- Deterministic tie-breaking is not cosmetic: if the encoder and decoder break ties differently, they build different trees and decoding produces garbage.
- Shannon's bound `H <= L < H + 1` is visible on real files: 4.403 vs 4.440 bits on English text. The gap comes from codes needing a whole number of bits.
- Bit-level I/O is mostly bookkeeping: an integer accumulator, a bit count, and the padding of the last byte.
- Order-0 statistics are a weak model of real data. The log file shows how much more there is to gain from repeated strings, which is why practical formats combine LZ77 and Huffman.

## Possible Improvements

- Canonical Huffman codes: store only the code length per symbol (at most 256 bytes) instead of 32-bit counts, which shrinks the header a lot
- Table-driven decoding (several bits at a time) instead of walking the tree per bit; it now decodes about 200 KB in 0.12 s
- Stream large files in blocks instead of reading them fully into memory (counts are 32-bit, so the current format is limited to 4 GB)
- Add a simple LZ77 stage in front to see how close it gets to zlib
