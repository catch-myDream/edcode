README.md File
Encoding and Decoding App

A Python app for encoding and decoding various formats, including Base64, URL, and more.

Features
* Supports multiple encoding and decoding formats:
	+ Base16
	+ Base32
	+ Base64
	+ URL
	+ Ascii85
	+ Base85
	+ ZeroMQ
* Options for customizing encoding and decoding behavior
* Support for reading input from files or strings
* Output can be written to files or printed to console

# Installation
```
pip install edcode
```

# Usage
```bash
edcode [options]

options:
  -h, --help            show this help message and exit

Input:
  -t TEXT, --text TEXT  Enter source (plain text)
  -f FILE, --file FILE  File name

Encoding:
  --b16e                Base 16 encode.
  --b32e                Base 32 encode.
  --b32hxe              Base 32 hex encode.
  --b64e                Base 64 encode.
  --usb64e              URL-Safe base 64 encode
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
  -m01 MAP01, --map01 MAP01
                        Map 0 and 1 to O and I.
  -ac ALTCHARS, --altchars ALTCHARS
                        Alternative characters for base 64
                        (e.g., :-_).
  -fs, --fspaces        Use special short sequence "y"
                        instead of 4 consecutive spaces.
  -wc WCOL, --wcol WCOL
                        Wrap output at specified column.
  -pd, --pad            Pad input to multiple of 4 before
                        encoding.
  -ad, --adobe          Use adobe framing ( <~ and ~> ) for
                        Ascii 85 encoding.
  -ic ICHARS, --ichars ICHARS
                        Ignore specified characters.
  -sf SAFE, --safe SAFE
                        Characters that should not be
                        quoted.
  -enc ENCODING, --encoding ENCODING
                        Specify the encoding (default:
                        utf-8)
  -err {strict,ignore,replace,xmlcharrefreplace,backslashreplace}, --errors {strict,ignore,replace,xmlcharrefreplace,backslashreplace}
                        Specify the error handling scheme
                        (default: strict)

Validation and Output:
  -vd, --vdate          Validate decoding.
  -o OUTPUT, --output OUTPUT
                        Output file name.


Examples
edcode -t "Hello, World!" --b64e

Output:
SGVsbG8sIFdvcmxkIQ==

edcode -t "SGVsbG8sIFdvcmxkIQ==" --b64d

Output:
Hello, World!

Developer
Mathan

This README.md file provides an overview of the app's features, usage, and options.

