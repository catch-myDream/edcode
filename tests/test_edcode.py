import os
import subprocess
import sys
import tempfile
import unittest

from edcode import encode_decode, main, str_to_bytes, bytes_to_str


class TestEdcodeCore(unittest.TestCase):
    def test_base16(self):
        encoded = encode_decode('b16e', b'hello')
        self.assertEqual(encoded, b'68656C6C6F')
        decoded = encode_decode('b16d', b'68656c6c6f', casefold=True)
        self.assertEqual(decoded, b'hello')

    def test_base32(self):
        encoded = encode_decode('b32e', b'hello')
        self.assertEqual(encoded, b'NBSWY3DP')
        decoded = encode_decode('b32d', b'nbswy3dp', casefold=True)
        self.assertEqual(decoded, b'hello')

    def test_base32_map01(self):
        # Base32 map01 maps '0' to 'O' and '1' to 'I'
        decoded = encode_decode('b32d', b'NBSWY3DP', map01=b'O')
        self.assertEqual(decoded, b'hello')

    def test_base32hex(self):
        encoded = encode_decode('b32hxe', b'hello')
        self.assertEqual(encoded, b'D1IMOR3F')
        decoded = encode_decode('b32hxd', b'd1imor3f', casefold=True)
        self.assertEqual(decoded, b'hello')

    def test_base64(self):
        encoded = encode_decode('b64e', b'hello world')
        self.assertEqual(encoded, b'aGVsbG8gd29ybGQ=')
        decoded = encode_decode('b64d', b'aGVsbG8gd29ybGQ=')
        self.assertEqual(decoded, b'hello world')

    def test_base64_altchars(self):
        encoded = encode_decode('b64e', b'\xfb\xef', altchars=b'-_')
        decoded = encode_decode('b64d', encoded, altchars=b'-_')
        self.assertEqual(decoded, b'\xfb\xef')

    def test_urlsafe_base64(self):
        data = b'\xfb\xef\xff'
        encoded = encode_decode('usb64e', data)
        self.assertNotIn(b'+', encoded)
        self.assertNotIn(b'/', encoded)
        decoded = encode_decode('usb64d', encoded)
        self.assertEqual(decoded, data)

    def test_ascii85(self):
        encoded = encode_decode('a85e', b'hello world', adobe=True)
        self.assertTrue(encoded.startswith(b'<~') and encoded.endswith(b'~>'))
        decoded = encode_decode('a85d', encoded, adobe=True)
        self.assertEqual(decoded, b'hello world')

    def test_base85(self):
        encoded = encode_decode('b85e', b'hello world')
        decoded = encode_decode('b85d', encoded)
        self.assertEqual(decoded, b'hello world')

    def test_z85(self):
        data = b'12345678'
        encoded = encode_decode('z85e', data)
        decoded = encode_decode('z85d', encoded)
        self.assertEqual(decoded, data)

    def test_z85_padding(self):
        data = b'hello'  # 5 bytes, not multiple of 4
        encoded = encode_decode('z85e', data, pad=True)
        self.assertIsNotNone(encoded)
        decoded = encode_decode('z85d', encoded)
        self.assertTrue(decoded.startswith(b'hello'))

    def test_url(self):
        raw = b'hello world&foo=bar'
        encoded = encode_decode('urle', raw)
        self.assertEqual(encoded, 'hello%20world%26foo%3Dbar')
        decoded = encode_decode('urld', encoded.encode())
        self.assertEqual(decoded, 'hello world&foo=bar')

    def test_binary_data_decode(self):
        # 0xff is invalid UTF-8
        raw_binary = b'\xff\xfe\x00\x01\x80'
        encoded = encode_decode('b64e', raw_binary)
        decoded = encode_decode('b64d', encoded)
        self.assertEqual(decoded, raw_binary)


class TestEdcodeCLI(unittest.TestCase):
    def test_cli_b64_roundtrip(self):
        code = main(['-t', 'test string', '--b64e'])
        self.assertEqual(code, 0)

    def test_cli_file_roundtrip(self):
        with tempfile.NamedTemporaryFile(delete=False) as in_file:
            in_file.write(b'\xff\xfe test binary')
            in_name = in_file.name

        with tempfile.NamedTemporaryFile(delete=False) as enc_file:
            enc_name = enc_file.name

        with tempfile.NamedTemporaryFile(delete=False) as dec_file:
            dec_name = dec_file.name

        try:
            # Encode file to enc_file
            code1 = main(['-f', in_name, '--b64e', '-o', enc_name])
            self.assertEqual(code1, 0)

            # Decode enc_file to dec_file
            code2 = main(['-f', enc_name, '--b64d', '-o', dec_name])
            self.assertEqual(code2, 0)

            with open(dec_name, 'rb') as f:
                result = f.read()
            self.assertEqual(result, b'\xff\xfe test binary')
        finally:
            for path in [in_name, enc_name, dec_name]:
                if os.path.exists(path):
                    os.remove(path)

    def test_cli_no_operation_error(self):
        code = main(['-t', 'hello'])
        self.assertEqual(code, 1)

    def test_cli_multiple_operations_error(self):
        code = main(['-t', 'hello', '--b64e', '--b16e'])
        self.assertEqual(code, 1)

    def test_cli_subprocess_stdin_piping(self):
        # Test piping via subprocess with python -m edcode
        proc = subprocess.run(
            [sys.executable, '-m', 'edcode', '--b64e'],
            input=b'piped content',
            capture_output=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), b'cGlwZWQgY29udGVudA==')


class TestLargeFileStreaming(unittest.TestCase):
    def test_speedups_status(self):
        import edcode.edcode as m
        if getattr(m, '_TESTING_PURE_PYTHON', False):
            self.skipTest("Testing pure Python fallback")
        from edcode import HAS_SPEEDUPS
        self.assertTrue(HAS_SPEEDUPS, "Expected C speedups module to be loaded")

    def test_streaming_large_roundtrips(self):
        # 2 MB binary test payload with non-uniform data
        payload = (b'The quick brown fox jumps over the lazy dog! \x00\xff\x80\x01\xfe' * 45000)
        
        pairs = [
            ('--b64e', '--b64d'),
            ('--usb64e', '--usb64d'),
            ('--b16e', '--b16d'),
            ('--b32e', '--b32d'),
            ('--b32hxe', '--b32hxd'),
            ('--b85e', '--b85d'),
            ('--z85e', '--z85d'),
            ('--urle', '--urld'),
        ]
        
        with tempfile.NamedTemporaryFile(delete=False) as f_in, \
             tempfile.NamedTemporaryFile(delete=False) as f_enc, \
             tempfile.NamedTemporaryFile(delete=False) as f_dec:
            in_file = f_in.name
            enc_file = f_enc.name
            dec_file = f_dec.name
            f_in.write(payload)

        try:
            for enc_flag, dec_flag in pairs:
                # Extra pad flag for z85 if payload not multiple of 4
                extra_args = ['-pd'] if enc_flag == '--z85e' else []
                # Encode file
                c1 = main(['-f', in_file, '-o', enc_file, enc_flag] + extra_args)
                self.assertEqual(c1, 0, f"Encode failed for {enc_flag}")

                # Decode file
                c2 = main(['-f', enc_file, '-o', dec_file, dec_flag])
                self.assertEqual(c2, 0, f"Decode failed for {dec_flag}")

                with open(dec_file, 'rb') as f:
                    recovered = f.read()

                if enc_flag == '--z85e':
                    # Pad flag may have appended null bytes to multiple of 4
                    self.assertTrue(recovered.startswith(payload), f"Roundtrip mismatch for {enc_flag}")
                else:
                    self.assertEqual(recovered, payload, f"Roundtrip mismatch for {enc_flag}")
        finally:
            for p in [in_file, enc_file, dec_file]:
                if os.path.exists(p):
                    os.remove(p)


class TestPackageImports(unittest.TestCase):
    def test_direct_edcode_package_imports(self):
        import edcode
        self.assertTrue(hasattr(edcode, 'encode_decode'))
        self.assertTrue(hasattr(edcode, 'stream_encode_decode'))
        self.assertTrue(hasattr(edcode, 'main'))
        self.assertEqual(edcode.__version__, "1.2.0")


if __name__ == '__main__':
    unittest.main()
