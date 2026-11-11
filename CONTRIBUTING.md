# Contributing to Edcode

Thank you for your interest in contributing to Edcode! We welcome bug reports, feature requests, documentation improvements, and code contributions.

---

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/catch-myDream/edcode.git
   cd edcode
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in editable mode**:
   ```bash
   pip install -e .
   ```

4. **Build the C accelerator in-place** (requires `clang` or `gcc`):
   ```bash
   python3 setup.py build_ext --inplace
   ```

---

## Running Tests

Run the test suite using `unittest`:
```bash
python3 -m unittest discover tests
```

To run tests without C speedups (testing pure-Python fallback):
```bash
python3 -c "
from unittest import defaultTestLoader, TextTestRunner
# Temporarily patch HAS_SPEEDUPS or rename .so
"
```

---

## Code Style & Guidelines

* Follow **PEP 8** style guidelines for Python code.
* For C extension changes (`edcode/_speedups.c`), maintain strict bounds-checking, ensure all Python references and buffer views are safely released on all return paths, and keep C-to-Python error reporting clean.
* Add unit tests in `tests/test_edcode.py` for any new features or bug fixes.
* Ensure all existing tests pass before submitting a pull request.

---

## Submitting Pull Requests

1. Fork the repository and create your feature branch from `main`:
   ```bash
   git checkout -b feature/my-cool-feature
   ```
2. Commit your changes with clear, descriptive commit messages:
   ```bash
   git commit -m "Add feature XYZ"
   ```
3. Push to your fork:
   ```bash
   git push origin feature/my-cool-feature
   ```
4. Open a Pull Request on GitHub against `main`.
