#!/usr/bin/env python3
"""
Edcode - High-performance Encoding and Decoding CLI utility and library.
Supports Base16, Base32, Base32Hex, Base64, URL-Safe Base64,
Ascii85, Base85, ZeroMQ (z85), and URL encoding/decoding.
Features streaming I/O for constant-memory processing of arbitrary large files
and native C accelerators for maximum performance.
"""

import argparse
import base64
import binascii
import io
import os
import sys
import urllib.parse
from typing import Any, BinaryIO, Dict, Optional, Union

# Try importing the optional high-performance C extension
try:
    from edcode import _speedups
    HAS_SPEEDUPS = True
except ImportError:
    try:
        import _speedups
        HAS_SPEEDUPS = True
    except ImportError:
        _speedups = None
        HAS_SPEEDUPS = False

DEFAULT_CHUNK_SIZE = 256 * 1024  # 256 KB

_Z85_ALPHABET = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?&<>()[]{}@%$#"
_Z85_DECODE_MAP = {c: i for i, c in enumerate(_Z85_ALPHABET)}

_B32_STD = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
_B32_HEX = b"0123456789ABCDEFGHIJKLMNOPQRSTUV"
_B32_TO_HEX_TRANS = bytes.maketrans(_B32_STD, _B32_HEX)
_HEX_TO_B32_TRANS = bytes.maketrans(_B32_HEX, _B32_STD)


def _py_b32hexencode(data: bytes) -> bytes:
    """Pure-Python fallback for Base32Hex encode (compatible with Python <3.10)."""
    if hasattr(base64, 'b32hexencode'):
        return base64.b32hexencode(data)
    return base64.b32encode(data).translate(_B32_TO_HEX_TRANS)


def _py_b32hexdecode(data: bytes, casefold: bool = False) -> bytes:
    """Pure-Python fallback for Base32Hex decode (compatible with Python <3.10)."""
    if hasattr(base64, 'b32hexdecode'):
        return base64.b32hexdecode(data, casefold=casefold)
    if casefold:
        data = data.upper()
    return base64.b32decode(data.translate(_HEX_TO_B32_TRANS), casefold=False)


def _py_z85encode(data: bytes) -> bytes:
    """Pure-Python fallback for ZeroMQ RFC 32 Z85 encoding."""
    if len(data) % 4 != 0:
        raise ValueError("Z85 length must be multiple of 4 bytes")
    if not data:
        return b""
    res = bytearray((len(data) // 4) * 5)
    j = 0
    for i in range(0, len(data), 4):
        val = (data[i] << 24) | (data[i + 1] << 16) | (data[i + 2] << 8) | data[i + 3]
        res[j] = _Z85_ALPHABET[val // 52200625]
        res[j + 1] = _Z85_ALPHABET[(val // 614125) % 85]
        res[j + 2] = _Z85_ALPHABET[(val // 7225) % 85]
        res[j + 3] = _Z85_ALPHABET[(val // 85) % 85]
        res[j + 4] = _Z85_ALPHABET[val % 85]
        j += 5
    return bytes(res)


def _py_z85decode(data: bytes) -> bytes:
    """Pure-Python fallback for ZeroMQ RFC 32 Z85 decoding."""
    if len(data) % 5 != 0:
        raise ValueError("Z85 length must be multiple of 5 characters")
    if not data:
        return b""
    res = bytearray((len(data) // 5) * 4)
    j = 0
    for i in range(0, len(data), 5):
        acc = 0
        for k in range(5):
            c = data[i + k]
            if c not in _Z85_DECODE_MAP:
                raise ValueError(f"bad z85 character at position {i + k}")
            acc = acc * 85 + _Z85_DECODE_MAP[c]
        if acc > 0xFFFFFFFF:
            raise ValueError(f"z85 overflow in hunk starting at byte {i}")
        res[j] = (acc >> 24) & 0xFF
        res[j + 1] = (acc >> 16) & 0xFF
        res[j + 2] = (acc >> 8) & 0xFF
        res[j + 3] = acc & 0xFF
        j += 4
    return bytes(res)


def str_to_bytes(s: Union[str, bytes], encoding: str = 'utf-8', errors: str = 'strict') -> bytes:
    """Convert input string to bytes if not already bytes."""
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode(encoding, errors=errors)
    return bytes(s)


def bytes_to_str(b: Union[str, bytes], encoding: str = 'utf-8', errors: str = 'strict') -> str:
    """Convert input bytes to string if not already a string."""
    if isinstance(b, str):
        return b
    if isinstance(b, bytes):
        return b.decode(encoding, errors=errors)
    return str(b)


def handler_func(func, *args, **kwargs) -> Optional[Any]:
    """Execute func with given arguments, printing error to stderr on failure."""
    try:
        return func(*args, **kwargs)
    except (TypeError, ValueError, binascii.Error) as e:
        sys.stderr.write(f"Error: {e}\n")
        return None
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        return None


def encode_decode(
    op: str,
    source: bytes,
    *,
    casefold: bool = False,
    map01: Optional[bytes] = None,
    altchars: Optional[bytes] = None,
    foldspaces: bool = False,
    wrapcol: int = 0,
    pad: bool = False,
    adobe: bool = False,
    ignorechars: bytes = b' \t\n\r\x0b',
    validate: bool = False,
    safe: str = '/',
    encoding: str = 'utf-8',
    errors: str = 'strict',
) -> Optional[Union[bytes, str]]:
    """
    Execute the specified encoding or decoding operation on source bytes.
    Uses native C speedups if available, with transparent fallback.
    """
    if op.endswith('d'):
        source = source.strip()

    # Base16
    if op == 'b16e':
        return handler_func(base64.b16encode, source)
    elif op == 'b16d':
        return handler_func(base64.b16decode, source, casefold=casefold)

    # Base32
    elif op == 'b32e':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.b32encode, source)
        return handler_func(base64.b32encode, source)
    elif op == 'b32d':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.b32decode, source, casefold=casefold, map01=map01)
        return handler_func(base64.b32decode, source, casefold=casefold, map01=map01)

    # Base32Hex
    elif op == 'b32hxe':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.b32hexencode, source)
        return handler_func(_py_b32hexencode, source)
    elif op == 'b32hxd':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.b32hexdecode, source, casefold=casefold)
        return handler_func(_py_b32hexdecode, source, casefold=casefold)

    # Base64
    elif op == 'b64e':
        return handler_func(base64.b64encode, source, altchars=altchars)
    elif op == 'b64d':
        return handler_func(base64.b64decode, source, altchars=altchars, validate=validate)

    # URL-Safe Base64
    elif op == 'usb64e':
        return handler_func(base64.urlsafe_b64encode, source)
    elif op == 'usb64d':
        return handler_func(base64.urlsafe_b64decode, source)

    # Ascii85
    elif op == 'a85e':
        if HAS_SPEEDUPS:
            return handler_func(
                _speedups.a85encode,
                source,
                foldspaces=foldspaces,
                wrapcol=wrapcol,
                pad=pad,
                adobe=adobe,
            )
        return handler_func(
            base64.a85encode,
            source,
            foldspaces=foldspaces,
            wrapcol=wrapcol,
            pad=pad,
            adobe=adobe,
        )
    elif op == 'a85d':
        if HAS_SPEEDUPS:
            return handler_func(
                _speedups.a85decode,
                source,
                foldspaces=foldspaces,
                adobe=adobe,
                ignorechars=ignorechars,
            )
        return handler_func(
            base64.a85decode,
            source,
            foldspaces=foldspaces,
            adobe=adobe,
            ignorechars=ignorechars,
        )

    # Base85
    elif op == 'b85e':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.b85encode, source, pad=pad)
        return handler_func(base64.b85encode, source, pad=pad)
    elif op == 'b85d':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.b85decode, source)
        return handler_func(base64.b85decode, source)

    # ZeroMQ (z85)
    elif op == 'z85e':
        if pad and len(source) % 4 != 0:
            source = source + b'\x00' * (4 - (len(source) % 4))
        if HAS_SPEEDUPS:
            return handler_func(_speedups.z85encode, source)
        return handler_func(_py_z85encode, source)
    elif op == 'z85d':
        if HAS_SPEEDUPS:
            return handler_func(_speedups.z85decode, source)
        return handler_func(_py_z85decode, source)

    # URL encode/decode
    elif op == 'urle':
        # Fast path directly from bytes
        safe_str = safe if safe else '/'
        try:
            return urllib.parse.quote_from_bytes(source, safe=safe_str)
        except Exception:
            string_val = bytes_to_str(source, encoding=encoding, errors=errors)
            return handler_func(urllib.parse.quote, string_val, safe=safe_str, encoding=encoding, errors=errors)
    elif op == 'urld':
        string_val = bytes_to_str(source, encoding=encoding, errors=errors)
        return handler_func(urllib.parse.unquote, string_val, encoding=encoding, errors=errors)

    else:
        sys.stderr.write(f"Error: Unknown operation '{op}'\n")
        return None


def _read_exact(stream: BinaryIO, n: int) -> bytes:
    """Read up to n bytes from stream, continuing across partial reads."""
    data = stream.read(n)
    if not data or len(data) == n:
        return data
    chunks = [data]
    remaining = n - len(data)
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def stream_encode_decode(
    op: str,
    in_stream: BinaryIO,
    out_stream: BinaryIO,
    *,
    casefold: bool = False,
    map01: Optional[bytes] = None,
    altchars: Optional[bytes] = None,
    foldspaces: bool = False,
    wrapcol: int = 0,
    pad: bool = False,
    adobe: bool = False,
    ignorechars: bytes = b' \t\n\r\x0b',
    validate: bool = False,
    safe: str = '/',
    encoding: str = 'utf-8',
    errors: str = 'strict',
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bool:
    """
    Stream encoding/decoding directly from in_stream to out_stream.
    Processes data in constant O(1) memory buffers, preventing memory spikes
    and maximizing CPU cache efficiency.
    Returns True on success, False on error.
    """
    try:
        # -------------------------------------------------------------
        # 1. STREAM ENCODING
        # -------------------------------------------------------------
        if op.endswith('e'):
            # Determine quantum size so intermediate chunks produce no padding
            quanta = {
                'b16e': 1,
                'b64e': 3,
                'usb64e': 3,
                'b32e': 5,
                'b32hxe': 5,
                'b85e': 4,
                'z85e': 4,
                'a85e': 4,
                'urle': 1,
            }
            q = quanta.get(op, 1)
            step = (max(chunk_size, q) // q) * q

            # Special Ascii85 handling when wrapcol or adobe framing is enabled
            if op == 'a85e' and (wrapcol > 0 or adobe or foldspaces):
                # For complex Ascii85 formatting options, encode via encode_decode
                # Ascii85 speedup module handles multi-megabytes directly with C speed
                raw_data = in_stream.read()
                res = encode_decode(
                    op, raw_data, foldspaces=foldspaces, wrapcol=wrapcol,
                    pad=pad, adobe=adobe, encoding=encoding, errors=errors
                )
                if res is None:
                    return False
                out_stream.write(res if isinstance(res, bytes) else res.encode(encoding, errors=errors))
                return True

            curr = _read_exact(in_stream, step)
            if not curr:
                # Empty input: produce valid empty output
                res = encode_decode(
                    op, b'', casefold=casefold, map01=map01, altchars=altchars,
                    foldspaces=foldspaces, wrapcol=wrapcol, pad=pad,
                    adobe=adobe, ignorechars=ignorechars, validate=validate,
                    safe=safe, encoding=encoding, errors=errors
                )
                if res is not None:
                    out_stream.write(res if isinstance(res, bytes) else res.encode(encoding, errors=errors))
                    return True
                return False

            while True:
                nxt = _read_exact(in_stream, step)
                is_final = len(nxt) == 0

                # Encode current chunk
                if op == 'b64e':
                    out_stream.write(base64.b64encode(curr, altchars=altchars))
                elif op == 'usb64e':
                    out_stream.write(base64.urlsafe_b64encode(curr))
                elif op == 'b16e':
                    out_stream.write(base64.b16encode(curr))
                elif op == 'b32e':
                    if HAS_SPEEDUPS:
                        out_stream.write(_speedups.b32encode(curr))
                    else:
                        out_stream.write(base64.b32encode(curr))
                elif op == 'b32hxe':
                    if HAS_SPEEDUPS:
                        out_stream.write(_speedups.b32hexencode(curr))
                    else:
                        out_stream.write(_py_b32hexencode(curr))
                elif op == 'b85e':
                    if is_final:
                        if HAS_SPEEDUPS:
                            out_stream.write(_speedups.b85encode(curr, pad=pad))
                        else:
                            out_stream.write(base64.b85encode(curr, pad=pad))
                    else:
                        if HAS_SPEEDUPS:
                            out_stream.write(_speedups.b85encode(curr, pad=False))
                        else:
                            out_stream.write(base64.b85encode(curr, pad=False))
                elif op == 'z85e':
                    if is_final and pad and len(curr) % 4 != 0:
                        curr = curr + b'\x00' * (4 - (len(curr) % 4))
                    if HAS_SPEEDUPS:
                        out_stream.write(_speedups.z85encode(curr))
                    else:
                        out_stream.write(_py_z85encode(curr))
                elif op == 'a85e':
                    if HAS_SPEEDUPS:
                        out_stream.write(_speedups.a85encode(curr, pad=pad))
                    else:
                        out_stream.write(base64.a85encode(curr, pad=pad))
                elif op == 'urle':
                    encoded_str = urllib.parse.quote_from_bytes(curr, safe=safe if safe else '/')
                    out_stream.write(encoded_str.encode('ascii'))

                if is_final:
                    break
                curr = nxt

            return True

        # -------------------------------------------------------------
        # 2. STREAM DECODING
        # -------------------------------------------------------------
        elif op.endswith('d'):
            # URL decoding stream
            if op == 'urld':
                rem = b''
                while True:
                    chunk = in_stream.read(chunk_size)
                    if not chunk:
                        break
                    data = rem + chunk
                    # Check for incomplete % escape at chunk boundary
                    if len(data) >= 1 and data[-1:] == b'%':
                        to_dec = data[:-1]
                        rem = data[-1:]
                    elif len(data) >= 2 and data[-2:-1] == b'%':
                        to_dec = data[:-2]
                        rem = data[-2:]
                    else:
                        to_dec = data
                        rem = b''
                    if to_dec:
                        out_stream.write(urllib.parse.unquote_to_bytes(to_dec))
                if rem:
                    out_stream.write(urllib.parse.unquote_to_bytes(rem))
                return True

            # Ascii85 decode
            if op == 'a85d':
                # Read input and decode with speedups
                raw_data = in_stream.read()
                res = encode_decode(
                    op, raw_data, foldspaces=foldspaces, adobe=adobe,
                    ignorechars=ignorechars, encoding=encoding, errors=errors
                )
                if res is None:
                    return False
                out_stream.write(res if isinstance(res, bytes) else res.encode(encoding, errors=errors))
                return True

            # Quantum-based block decoders: b16d, b64d, usb64d, b32d, b32hxd, b85d, z85d
            quanta = {
                'b16d': 2,
                'b64d': 4,
                'usb64d': 4,
                'b32d': 8,
                'b32hxd': 8,
                'b85d': 5,
                'z85d': 5,
            }
            q = quanta.get(op, 1)
            rem = b''

            while True:
                chunk = in_stream.read(chunk_size)
                if not chunk:
                    break
                clean = chunk.translate(None, b' \t\r\n\x0b')
                if not clean:
                    continue
                data = rem + clean

                # For padded base64 and base32, '=' marks the beginning of the final padded quantum
                if op in ('b64d', 'usb64d', 'b32d', 'b32hxd') and b'=' in data:
                    idx = data.index(b'=')
                    safe_len = (idx // q) * q
                    to_dec = data[:safe_len]
                    rem = data[safe_len:]
                else:
                    n = (len(data) // q) * q
                    to_dec = data[:n]
                    rem = data[n:]

                if to_dec:
                    decoded = encode_decode(
                        op, to_dec, casefold=casefold, map01=map01, altchars=altchars,
                        validate=validate, encoding=encoding, errors=errors
                    )
                    if decoded is None:
                        return False
                    out_stream.write(decoded if isinstance(decoded, bytes) else decoded.encode(encoding, errors=errors))

            if rem:
                decoded = encode_decode(
                    op, rem, casefold=casefold, map01=map01, altchars=altchars,
                    validate=validate, encoding=encoding, errors=errors
                )
                if decoded is None:
                    return False
                out_stream.write(decoded if isinstance(decoded, bytes) else decoded.encode(encoding, errors=errors))

            return True

        else:
            sys.stderr.write(f"Error: Unknown operation '{op}'\n")
            return False

    except (TypeError, ValueError, binascii.Error) as e:
        sys.stderr.write(f"Error: {e}\n")
        return False
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except OSError:
            pass
        return True
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        return False


def build_parser() -> argparse.ArgumentParser:
    """Build and return argument parser."""
    parser = argparse.ArgumentParser(
        prog='edcode',
        description='Encode and decode multiple data formats from terminal, file, or stdin.',
        usage='%(prog)s [options]'
    )

    input_group = parser.add_argument_group('Input')
    input_group.add_argument('-t', '--text', help='Enter source (plain text)')
    input_group.add_argument('-f', '--file', help='Input file name')

    encoding_group = parser.add_argument_group('Encoding')
    encoding_group.add_argument('--b16e', action='store_true', help='Base 16 encode.')
    encoding_group.add_argument('--b32e', action='store_true', help='Base 32 encode.')
    encoding_group.add_argument('--b32hxe', action='store_true', help='Base 32 hex encode.')
    encoding_group.add_argument('--b64e', action='store_true', help='Base 64 encode.')
    encoding_group.add_argument('--usb64e', action='store_true', help='URL-Safe base 64 encode.')
    encoding_group.add_argument('--a85e', action='store_true', help='Ascii 85 encode.')
    encoding_group.add_argument('--b85e', action='store_true', help='Base 85 encode.')
    encoding_group.add_argument('--z85e', action='store_true', help='ZeroMQ encode.')
    encoding_group.add_argument('--urle', action='store_true', help='URL encode.')

    decoding_group = parser.add_argument_group('Decoding')
    decoding_group.add_argument('--b16d', action='store_true', help='Base 16 decode.')
    decoding_group.add_argument('--b32d', action='store_true', help='Base 32 decode.')
    decoding_group.add_argument('--b32hxd', action='store_true', help='Base 32 hex decode.')
    decoding_group.add_argument('--b64d', action='store_true', help='Base 64 decode.')
    decoding_group.add_argument('--usb64d', action='store_true', help='URL-Safe base 64 decode.')
    decoding_group.add_argument('--a85d', action='store_true', help='Ascii 85 decode.')
    decoding_group.add_argument('--b85d', action='store_true', help='Base 85 decode.')
    decoding_group.add_argument('--z85d', action='store_true', help='ZeroMQ decode.')
    decoding_group.add_argument('--urld', action='store_true', help='URL decode.')

    option_group = parser.add_argument_group('Options')
    option_group.add_argument('-cf', '--cfold', action='store_true', help='Accept lowercase alphabet as input.')
    option_group.add_argument('-m01', '--map01', help='Map 0 and 1 to O and I (Base 32).')
    option_group.add_argument('-ac', '--altchars', help='Alternative characters for base 64 (e.g., :-_).')
    option_group.add_argument('-fs', '--fspaces', action='store_true', help='Use special short sequence "y" instead of 4 consecutive spaces.')
    option_group.add_argument('-wc', '--wcol', default=0, type=int, help='Wrap output at specified column.')
    option_group.add_argument('-pd', '--pad', action='store_true', help='Pad input to multiple of 4 before encoding.')
    option_group.add_argument('-ad', '--adobe', action='store_true', help='Use adobe framing ( <~ and ~> ) for Ascii 85.')
    option_group.add_argument('-ic', '--ichars', default=b' \t\n\r\x0b', help='Ignore specified characters.')
    option_group.add_argument('-sf', '--safe', help='Characters that should not be quoted (URL).')
    option_group.add_argument('-enc', '--encoding', default='utf-8', help='Specify the encoding (default: utf-8).')
    option_group.add_argument(
        '-err',
        '--errors',
        default='strict',
        help='Specify the error handling scheme (default: strict).',
        choices=['strict', 'ignore', 'replace', 'xmlcharrefreplace', 'backslashreplace']
    )

    output_group = parser.add_argument_group('Validation and Output')
    output_group.add_argument('-vd', '--vdate', action='store_true', help='Validate decoding.')
    output_group.add_argument('-o', '--output', help='Output file name.')

    return parser


OPERATIONS = [
    'b16e', 'b16d', 'b32e', 'b32d', 'b32hxe', 'b32hxd',
    'b64e', 'b64d', 'usb64e', 'usb64d', 'a85e', 'a85d',
    'b85e', 'b85d', 'z85e', 'z85d', 'urle', 'urld'
]


def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # 1. Check operation flags
    chosen_ops = [op for op in OPERATIONS if getattr(args, op, False)]
    if not chosen_ops:
        parser.print_help(sys.stderr)
        sys.stderr.write("\nError: Please specify an encoding or decoding option (e.g. --b64e, --b64d).\n")
        return 1

    if len(chosen_ops) > 1:
        sys.stderr.write(
            f"Error: Multiple operations specified ({', '.join('--' + op for op in chosen_ops)}). Please choose only one.\n"
        )
        return 1

    active_op = chosen_ops[0]

    # Parse helper options
    map01_bytes = str_to_bytes(args.map01, encoding=args.encoding, errors=args.errors) if args.map01 else None
    altchars_bytes = str_to_bytes(args.altchars, encoding=args.encoding, errors=args.errors) if args.altchars else None
    ichars_bytes = str_to_bytes(args.ichars, encoding=args.encoding, errors=args.errors) if isinstance(args.ichars, str) else args.ichars

    # 2. Setup input source
    in_file_obj: Optional[BinaryIO] = None
    close_in = False

    if args.text is not None:
        raw_bytes = args.text.encode(args.encoding, errors=args.errors)
        in_file_obj = io.BytesIO(raw_bytes)
    elif args.file is not None:
        try:
            in_file_obj = open(args.file, 'rb', buffering=DEFAULT_CHUNK_SIZE)
            close_in = True
        except FileNotFoundError:
            sys.stderr.write(f'Error: File "{args.file}" not found\n')
            return 1
        except OSError as e:
            sys.stderr.write(f'Error reading "{args.file}": {e}\n')
            return 1
    elif not sys.stdin.isatty():
        in_file_obj = sys.stdin.buffer
    else:
        sys.stderr.write("Error: No input provided. Use -t/--text, -f/--file, or pipe input via stdin.\n")
        return 1

    # 3. Setup output target
    out_file_obj: Optional[BinaryIO] = None
    close_out = False

    if args.output:
        try:
            out_file_obj = open(args.output, 'wb', buffering=DEFAULT_CHUNK_SIZE)
            close_out = True
        except OSError as e:
            sys.stderr.write(f'Error writing to output file "{args.output}": {e}\n')
            if close_in and in_file_obj:
                in_file_obj.close()
            return 1
    else:
        out_file_obj = sys.stdout.buffer

    # 4. Stream execution
    try:
        success = stream_encode_decode(
            active_op,
            in_file_obj,
            out_file_obj,
            casefold=args.cfold,
            map01=map01_bytes,
            altchars=altchars_bytes,
            foldspaces=args.fspaces,
            wrapcol=args.wcol,
            pad=args.pad,
            adobe=args.adobe,
            ignorechars=ichars_bytes,
            validate=args.vdate,
            safe=args.safe if args.safe else '/',
            encoding=args.encoding,
            errors=args.errors,
            chunk_size=DEFAULT_CHUNK_SIZE,
        )

        if not success:
            return 1

        # Flush buffer
        out_file_obj.flush()

        # If writing to console/stdout and operation was encoding or text output, append newline for clean CLI output
        if not args.output:
            if active_op.endswith('e') or sys.stdout.isatty():
                try:
                    sys.stdout.buffer.write(b'\n')
                    sys.stdout.buffer.flush()
                except (BrokenPipeError, OSError):
                    pass

        return 0

    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except OSError:
            pass
        return 0
    finally:
        if close_in and in_file_obj:
            in_file_obj.close()
        if close_out and out_file_obj:
            out_file_obj.close()


if __name__ == '__main__':
    sys.exit(main())
