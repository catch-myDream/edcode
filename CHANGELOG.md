# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-11-10

### Added
* **Streaming I/O Architecture**: Added `stream_encode_decode()` supporting constant $O(1)$ memory usage (~256 KB - 512 KB) for arbitrarily large files (multi-gigabyte files now process with zero risk of out-of-memory errors).
* **Native C Speedups Extension**: Added optional C extension (`edcode._speedups`) with native bitwise loops for Base32, Base32Hex, Base85, Z85, and Ascii85, boosting throughput up to 375+ MB/s.
* **Large File Roundtrip Tests**: Comprehensive streaming tests across all 18 codec operations.
* **GitHub Actions CI/CD**: Added multi-platform automated testing and PyPI publishing workflows.

### Changed
* Optimized URL percent-encoding to quote directly from raw bytes, eliminating intermediate string decoding scans.
* Direct buffered binary streaming to `sys.stdout.buffer` for clean and fast pipe output.
* Packaging modernized with PEP 621 metadata, `MANIFEST.in`, and robust fallback handling if a C compiler is absent.

### Fixed
* Fixed severe memory accumulation and CPU bottlenecks on large files.
* Fixed unexpected error handling when binary data contains non-UTF-8 bytes.

---

## [1.1.0] - 2026-11-09

### Added
* Support for ZeroMQ (`--z85e`, `--z85d`) and URL percent-encoding (`--urle`, `--urld`).
* Auto-padding support (`-pd`, `--pad`) for 4-byte boundaries.
* Stdin stream piping support for CLI chaining.

---

## [1.0.0] - 2026-11-08

### Added
* Initial release of Edcode CLI and library.
* Support for Base16, Base32, Base32Hex, Base64, URL-Safe Base64, and Ascii85.
* CLI options for custom mapping, casefold, and output wrapping.
