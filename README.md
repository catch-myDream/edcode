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

Usage
```bash
python app.py [options]

Options
- `-t`, `--text`: Input string to encode or decode
- `-f`, `--file`: Input file to encode or decode
- `--b16e`, `--b32e`, `--b64e`, etc.: Encoding options
- `--b16d`, `--b32d`, `--b64d`, etc.: Decoding options
- `-cf`, `--cfold`: Accept lowercase alphabet as input
- `-m01`, `--map01`: Map 0 and 1 to O and I
- `-ac`, `--altchars`: Alternative characters for base64
- `-fs`, `--fspaces`: Use special short sequence "y" instead of 4 consecutive spaces
- `-wc`, `--wcol`: Wrap output at specified column
- `-pd`, `--pad`: Pad input to multiple of 4 before encoding
- `-ad`, `--adobe`: Use adobe framing ( <~ and ~> ) for Ascii 85 encoding
- `-ic`, `--ichars`: Ignore specified characters
- `-sf`, `--safe`: Characters that should not be quoted
- `-enc`, `--encoding`: Specify the encoding (default: utf-8)
- `-err`, `--errors`: Specify the error handling scheme (default: strict)
- `-vd`, `--vdate`: Validate decoding
- `-o`, `--output`: Output file name

Examples
python app.py -t "Hello, World!" --b64e

Output:
SGVsbG8sIFdvcmxkIQ==

python app.py -t "SGVsbG8sIFdvcmxkIQ==" --b64d

Output:
Hello, World!

Developer
Mathan

This README.md file provides an overview of the app's features, usage, and options.

