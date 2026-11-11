# Edcode

[![CI](https://github.com/Mathan-M/edcode/actions/workflows/ci.yml/badge.svg)](https://github.com/Mathan-M/edcode/actions/workflows/ci.yml)
[![PyPI Version](https://img.shields.io/pypi/v/edcode.svg)](https://pypi.org/project/edcode/)
[![Python Versions](https://img.shields.io/pypi/pyversions/edcode.svg)](https://pypi.org/project/edcode/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

A high-performance command-line utility and Python library for encoding and decoding data across various formats, including Base16, Base32, Base32Hex, Base64, URL-Safe Base64, Ascii85, Base85, ZeroMQ (z85), and URL quoting.

Engineered with a **chunked streaming I/O architecture** for constant $O(1)$ memory usage and **native C bitwise accelerators**, capable of encoding and decoding multi-gigabyte files at speeds exceeding **375 MB/s**.

---

## Features

* **High Performance & Streaming Engine**:
  * **$O(1)$ Constant Memory**: Streams arbitrarily large files (gigabytes) in fixed 256 KB chunks without memory spikes or out-of-memory errors.
  * **Native C Speedups**: Optional native C accelerator (`edcode._speedups`) delivering up to 375+ MB/s throughput for Base32, Base85, Z85, and Ascii85.
  * **Zero Dependencies & Portability**: Standard library-compatible with automatic pure-Python fallback if no C compiler is available.
* **Supported Formats**:
  * Base16 (Hex)
  * Base32 & Base32-Hex
  * Base64 & URL-Safe Base64
  * Ascii85 & Base85
  * ZeroMQ (Z85)
  * URL percent-encoding
* **Flexible I/O**:
  * Input from string (`-t / --text`), file (`-f / --file`), or pipe via standard input (`stdin`).
  * Output to console or file (`-o / --output`).
  * Safe handling of arbitrary binary data (images, archives, cryptographic keys).
* **Customizable Parameters**:
  * Casefold support, custom Base32 map01, custom Base64 altchars.
  * Ascii85 space folding (`-fs`), adobe framing (`-ad`, `<~` ... `~>`), and column wrapping (`-wc`).
  * Auto-padding for 4-byte boundaries (`-pd`).
  * Configurable charset encodings and error handlers.

---

## Installation

### From PyPI

```bash
pip install edcode
```

### From Source

```bash
git clone https://github.com/Mathan-M/edcode.git
cd edcode
pip install .
```

To build the optional C accelerator locally:
```bash
python3 setup.py build_ext --inplace
```

---

## Usage

### Command-Line Interface

```bash
edcode [options]
```

#### Options Overview

```text
Input:
  -t, --text TEXT       Enter source (plain text)
  -f, --file FILE       Input file name

Encoding:
  --b16e                Base 16 encode.
  --b32e                Base 32 encode.
  --b32hxe              Base 32 hex encode.
  --b64e                Base 64 encode.
  --usb64e              URL-Safe base 64 encode.
  --a85e                Ascii 85 encode.
  --b85e                Base 85 encode.
  --z85e                ZeroMQ encode.
  --urle                URL encode.

Decoding:
  --b16d                Base 16 decode.
  --b32d                Base 32 decode.
  --b32hxd              Base 32 hex decode.
  --b64d                Base 64 decode.
  --usb64d              URL-Safe base 64 decode.
  --a85d                Ascii 85 decode.
  --b85d                Base 85 decode.
  --z85d                ZeroMQ decode.
  --urld                URL decode.

Options:
  -cf, --cfold          Accept lowercase alphabet as input.
  -m01, --map01 MAP01   Map 0 and 1 to O and I (Base 32).
  -ac, --altchars ALTCHARS
                        Alternative characters for base 64 (e.g., :-_).
  -fs, --fspaces        Use special short sequence "y" instead of 4 consecutive spaces.
  -wc, --wcol WCOL      Wrap output at specified column.
  -pd, --pad            Pad input to multiple of 4 before encoding.
  -ad, --adobe          Use adobe framing ( <~ and ~> ) for Ascii 85.
  -ic, --ichars ICHARS  Ignore specified characters.
  -sf, --safe SAFE      Characters that should not be quoted (URL).
  -enc, --encoding ENCODING
                        Specify the encoding (default: utf-8).
  -err, --errors {strict,ignore,replace,xmlcharrefreplace,backslashreplace}
                        Specify error handling scheme (default: strict).

Validation and Output:
  -vd, --vdate          Validate decoding.
  -o, --output OUTPUT   Output file name.
```

---

## CLI Examples

### Text Encoding & Decoding
```bash
# Base64 Encode
edcode -t "Hello, World!" --b64e
# Output: SGVsbG8sIFdvcmxkIQ==

# Base64 Decode
edcode -t "SGVsbG8sIFdvcmxkIQ==" --b64d
# Output: Hello, World!
```

### Stdin Piping
```bash
echo "Hello, World!" | edcode --b64e
echo "SGVsbG8sIFdvcmxkIQ==" | edcode --b64d
```

### File Processing (Streaming)
```bash
# Encode large file to output file
edcode -f large_archive.tar.gz --b64e -o encoded.txt

# Decode file back to binary
edcode -f encoded.txt --b64d -o recovered_archive.tar.gz
```

---

## Python API Usage

### In-Memory Encoding and Decoding

```python
import edcode

# Base64 encode
encoded = edcode.encode_decode('b64e', b'hello world')
print(encoded)  # b'aGVsbG8gd29ybGQ='

# Base64 decode
decoded = edcode.encode_decode('b64d', encoded)
print(decoded)  # b'hello world'

# Base85 with custom padding
b85_enc = edcode.encode_decode('b85e', b'sensitive data', pad=True)
b85_dec = edcode.encode_decode('b85d', b85_enc)
```

### Stream Processing (Files / Sockets / Streams)

```python
import edcode

# Stream encode a 10 GB file with constant ~256 KB memory usage
with open("source.iso", "rb") as fin, open("source.iso.b64", "wb") as fout:
    edcode.stream_encode_decode("b64e", fin, fout)

# Stream decode back to binary
with open("source.iso.b64", "rb") as fin, open("restored.iso", "wb") as fout:
    edcode.stream_encode_decode("b64d", fin, fout)
```

---

## Performance Benchmark

Measured throughput processing a 50 MB payload:

| Codec | Encode Speed | Decode Speed | Peak Memory |
| :--- | :--- | :--- | :--- |
| **ZeroMQ (Z85)** | **376 MB/s** | **212 MB/s** | < 1 MB |
| **Base85** | **364 MB/s** | **195 MB/s** | < 1 MB |
| **Base32** | **319 MB/s** | **163 MB/s** | < 1 MB |
| **Base64** | **167 MB/s** | **172 MB/s** | < 1 MB |

---

## Running Tests

Run the full test suite using Python's standard `unittest`:

```bash
python3 -m unittest discover tests
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on setting up a development environment, code guidelines, and the pull request process.

---

## License

This project is licensed under the [GNU General Public License v3.0 or later](LICENSE) (GPL-3.0-or-later).
