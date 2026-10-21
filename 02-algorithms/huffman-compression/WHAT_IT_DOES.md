# huffman-compression — What it does

## In one sentence
A command-line tool that compresses and decompresses any file with Huffman coding (frequent bytes get short bit codes, rare bytes get long ones) and reports how close the result is to the theoretical limit given by the file's Shannon entropy.

## The problem it solves
Most files use some byte values much more often than others; in English text, the space and the letter `e` are far more common than `z`. Huffman coding exploits this by replacing each fixed 8-bit byte with a variable-length code, and it is still a building block inside zip, gzip, PNG and JPEG. This tool performs the full round trip on real files and shows, with numbers, how much such a code saves, where the limit is, and where it does poorly (random data, repetitive text) compared with zlib.

## Input
- `compress INPUT OUTPUT` — any file (text or binary) and the path for the compressed result.
- `decompress INPUT OUTPUT` — a file previously produced by `compress` and the path for the restored file.
- `stats INPUT [--top N]` — any file; `--top` sets how many of the most frequent byte values to list (default 10).
- OUTPUT must be a different file from INPUT.
- `examples/make_random.py OUTPUT [--size BYTES] [--seed N]` — writes seeded random bytes (default 20,000 bytes, seed 0) to show incompressible data.

## How it works
1. **Count bytes** (`huffman.py`, `compress`): reads the whole file into memory and counts how often each of the 256 possible byte values appears (`collections.Counter`).
2. **Build the tree** (`build_tree`): puts every byte value into a priority queue (`heapq`) as `(count, order, node)`. It repeatedly removes the two least frequent nodes and inserts a parent whose count is their sum, until one node (the root) remains. `order` is the byte value for leaves and an increasing counter for new parent nodes, so ties are always broken the same way; this lets the decoder rebuild exactly the same tree.
3. **Assign codes** (`build_codes`): walks the tree, adding `0` for each left branch and `1` for each right branch. Because every byte value is a leaf, no code is the beginning of another (prefix-free). If the file has only one distinct byte value, it gets the code `0` (1 bit per byte).
4. **Pack bits**: appends each byte's code to an integer buffer and writes out a full byte every time 8 bits are ready. The last byte is padded with zero bits.
5. **Write the file**: a header then the packed data. Header layout: magic `HUF1` (4 bytes), number of distinct symbols (2 bytes), 5 bytes per symbol (byte value + 32-bit count), and 1 byte giving the number of padding bits. An empty input becomes just the 7-byte header.
6. **Decompress** (`read_header`, `decompress`): checks the `HUF1` magic, reads the frequency table and padding, rebuilds the same tree, then reads the data bit by bit, walking the tree from the root and emitting a byte at each leaf. It checks that the number of decoded bytes equals the total in the table and reports truncated or corrupted files.
7. **Statistics** (`cmd_stats`): computes the Shannon entropy in bits per symbol (`sum of p * log2(1/p)`, function `entropy`), the Huffman average code length weighted by frequency (`average_length`), the payload size versus the entropy bound (`ceil(entropy x size / 8)`), the header size (`7 + 5 x distinct symbols`), the overall ratio, the size `zlib.compress(data, 9)` would produce (for reference only), and a table of the top N byte values with count, share and code.

## Output
- `compress` writes the compressed file and prints sizes before/after and the percentage.
- `decompress` writes the restored file (byte-for-byte identical to the original) and prints the restored size.
- `stats` prints a report to the console and writes no files.
- Exit codes: `0` = ok; `2` = missing file, not a file made by this tool, corrupted/truncated data, or OUTPUT equal to INPUT.

```text
$ python huffman.py compress examples/english.txt english.huf
examples/english.txt -> english.huf: 4,183 -> 2,659 bytes (63.6% of original)

$ python huffman.py stats examples/english.txt --top 3
File:              examples/english.txt (4,183 bytes, 66 distinct)
Entropy:           4.403 bits/symbol
Huffman average:   4.440 bits/symbol  (+0.037 over entropy)
Payload:           2,322 bytes  (entropy bound 2,303)
Header:            337 bytes
Compressed total:  2,659 bytes = 63.6% of original (ratio 1.57:1)
zlib -9 (LZ77 + Huffman), for reference: 2,047 bytes = 48.9%

Top 3 symbols
  symbol     count   share  code
  ' '          725   17.3%  111
  'e'          407    9.7%  001
  't'          318    7.6%  1011
```

## Files
- `huffman.py` — the whole tool: tree building, code assignment, bit packing, file format, decoding, entropy statistics and the `compress` / `decompress` / `stats` command-line interface.
- `examples/english.txt` — about 4 KB of English prose.
- `examples/access.log` — 140 lines of a synthetic web server log (repetitive strings).
- `examples/make_random.py` — writes seeded random bytes to show that random data does not compress.
- `tests/test_huffman.py` — pytest tests (round trips including empty and single-symbol files, prefix-free codes, entropy bound, header/padding, rejection of foreign and truncated files).
- `HOW_TO_RUN.txt`, `README.md` — usage instructions and documentation.

## What it does not do
- It only uses single-byte frequencies; it does not detect repeated words or strings (no LZ77 stage), so repetitive files like logs compress far less than with zlib.
- It does not shrink random or already-compressed data (JPEG, PDF, zip); with the header such files can get larger (about 106% for the 20 KB random example).
- It reads the whole file into memory and stores counts as 32-bit numbers, so it is not meant for very large files (format limit of 4 GB).
- It stores full counts in the header rather than compact canonical code lengths, so the header is relatively large on small files.
- The `.huf` format is its own; other tools cannot open it, and it does not compress folders or multiple files.
