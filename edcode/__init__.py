"""
Edcode - Encoding and Decoding utility library and CLI.
"""

from .edcode import (
    main,
    encode_decode,
    stream_encode_decode,
    str_to_bytes,
    bytes_to_str,
    build_parser,
    OPERATIONS,
    HAS_SPEEDUPS,
)

__version__ = "1.2.0"

__all__ = [
    "main",
    "encode_decode",
    "stream_encode_decode",
    "str_to_bytes",
    "bytes_to_str",
    "build_parser",
    "OPERATIONS",
    "HAS_SPEEDUPS",
    "__version__",
]
