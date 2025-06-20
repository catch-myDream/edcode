#!/usr/bin/env python3

# Author and devoloper Mathan

import base64
import argparse
import urllib.parse

# This function to convert string to bytes
def str_to_bytes(s):
    if isinstance(s,str):
        return s.encode()
    return s

# This function to convert bytes to string
def bytes_to_str(b):
    if isinstance(b,bytes):
        return b.decode()
    return b

# This function to handle error, encoding and decoding
# operations
def handler_func(func,*args,**kwargs):
    try:
        return func(*args,**kwargs)
    except (TypeError, ValueError) as e:
        print(f'Error {e}')
        return None


def main():
    # Create an ArgumantParser object to parse
    # command-line arguments
    parser = argparse.ArgumentParser(usage='%(prog)s [options]')

    # Define input group
    input_group = parser.add_argument_group('Input')

    # Add arguments for input text and file 
    input_group.add_argument('-t','--text',help='Enter source (plain text)')
    input_group.add_argument('-f','--file',help='File name')

    # Dedine encoding group
    encoding_group = parser.add_argument_group('Encoding')

    # Add arguments for different encoding options
    encoding_group.add_argument('--b16e',action='store_true',help='Base 16 encode.')
    encoding_group.add_argument('--b32e',action='store_true',help='Base 32 encode.')
    encoding_group.add_argument('--b32hxe',action='store_true',help='Base 32 hex encode.')
    encoding_group.add_argument('--b64e',action='store_true',help='Base 64 encode.')
    encoding_group.add_argument('--usb64e',action='store_true',help='URL-Safe base 64 encode')
    encoding_group.add_argument('--a85e',action='store_true',help='Ascii 85 encode.')
    encoding_group.add_argument('--b85e',action='store_true',help='Base 85 encode.')
    encoding_group.add_argument('--z85e',action='store_true',help='ZeroMQ encode.')
    encoding_group.add_argument('--urle',action='store_true',help='URL encode.')

    # Define decoding group
    decoding_group = parser.add_argument_group('Decoding')
    # Add argument for different decoding options
    decoding_group.add_argument('--b16d',action='store_true',help='Base 16 decode.')
    decoding_group.add_argument('--b32d',action='store_true',help='Base 32 decode.')
    decoding_group.add_argument('--b32hxd',action='store_true',help='Base 32 hex decode.')
    decoding_group.add_argument('--b64d',action='store_true',help='Base 64 decode.')
    decoding_group.add_argument('--usb64d',action='store_true',help='URL-Safe base 64 decode.')
    decoding_group.add_argument('--a85d',action='store_true',help='Ascii 85 decode.')
    decoding_group.add_argument('--b85d',action='store_true',help='Base 85 decode.')
    decoding_group.add_argument('--z85d',action='store_true',help='ZeroMQ decode.')
    decoding_group.add_argument('--urld',action='store_true',help='URL decode.')

    # Define option group
    option_group = parser.add_argument_group('Options')

    # Add argument for different flags
    option_group.add_argument('-cf','--cfold',action='store_true',help='Accept lowercase alphabet as input.')
    option_group.add_argument('-m01','--map01',help='Map 0 and 1 to O and I.')
    option_group.add_argument('-ac','--altchars',help='Alternative characters for base 64 (e.g., :-_).')
    option_group.add_argument('-fs','--fspaces',action='store_true',help='Use special short sequence "y" instead of 4 consecutive spaces.')
    option_group.add_argument('-wc','--wcol',default=0,help='Wrap output at specified column.')
    option_group.add_argument('-pd','--pad',action='store_true',help='Pad input to  multiple of 4 before encoding.')
    option_group.add_argument('-ad','--adobe',action='store_true',help='Use adobe framing ( <~ and ~> ) for Ascii 85 encoding.')
    option_group.add_argument('-ic','--ichars',default=b' \t\n\r\x0b',help='Ignore specified characters.')

    option_group.add_argument('-sf','--safe',help='Characters that should not be quoted.')
    option_group.add_argument('-enc','--encoding',default='utf-8',help='Specify the encoding (default: utf-8)')
    option_group.add_argument('-err','--errors',default='strict',help='Specify the error handling scheme (default: strict)',choices=['strict','ignore','replace','xmlcharrefreplace','backslashreplace'])

    # Define output group and validate
    output_group = parser.add_argument_group('Validation and Output')
    output_group.add_argument('-vd','--vdate',action='store_true',help='Validate decoding.')
    output_group.add_argument('-o','--output',help='Output file name.')

    # Parse command-line arguments
    args = parser.parse_args()

    # Determine the source of the input (text or file)
    source = ''
    res = ''

    if(args.text):
        # Convert the the input text to bytes
        source = str_to_bytes(args.text)
    elif(args.file):
        # Read the input file and convert its contents
        # to bytes
        try:
            with open(args.file,'r') as f:
                source = str_to_bytes(f.read()).strip()
                f.close()

        except FileNotFoundError:
            print(f'"{args.file}" File not found')
            return

    
    # Perform the specified encoding or decoding operation
    if(args.b16e):
        res = handler_func(base64.b16encode,source)
        
    elif(args.b16d):
        a = {'s': source,
             'casefold': True if args.cfold else False}
        res = handler_func(base64.b16decode,**a)


    elif(args.b32e):
        res = handler_func(base64.b32encode,source)

    elif(args.b32d):
        a = {'s': source,
             'casefold': True if args.cfold else False,
             'map01': str_to_bytes(args.map01) if args.map01 else None
            }

        res = handler_func(base64.b32decode,**a)


    elif(args.b32hxe):
        res = handler_func(base64.b32hexencode,source)

    elif(args.b32hxd):
        a = {'s': source,
             'casefold': True if args.cfold else False
             }
        res = handler_func(base64.b32hexdecode,**a)


    elif(args.b64e):
        a = {'s': source,
             'altchars': str_to_bytes(args.altchars) if args.altchars else None
             }

        res = handler_func(base64.b64encode,**a)

    elif(args.b64d):
        a = {'s': source,
             'altchars': str_to_bytes(args.altchars) if args.altchars else None,
             'validate': True if args.vdate else False
             }
        res = handler_func(base64.b64decode,**a)


    elif(args.usb64e):
        res = handler_func(base64.urlsafe_b64encode,source)

    elif(args.usb64d):
        res = handler_func(base64.urlsafe_b64decode,source)

    elif(args.a85e):
        a = {'b': source,
             'foldspaces': True if args.fspaces else False,
             'pad': True if args.pad else False,
             'wrapcol': int(args.wcol) if args.wcol else 0,
             'adobe': True if args.adobe else False
             }

        res = handler_func(base64.a85encode,**a)

    elif(args.a85d):
        a = {'b': source,
             'foldspaces': True if args.fspaces else False,
             'adobe': True if args.adobe else False,
             'ignorechars': str_to_bytes(args.ichars) if args.ichars else b' \t\n\r\x0b'
             }
        res = handler_func(base64.a85decode,**a)

    elif(args.b85e):
        a = {'b': source,
             'pad': True if args.pad else False
             }
        res = handler_func(base64.b85encode,**a)

    elif(args.b85d):
        res = handler_func(base64.b85decode,source)

    elif(args.z85e):
        res = handler_func(base64.z85encode,source)
    elif(args.z85d):
        res = handler_func(base64.z85decode,source)


    elif(args.urle):
        a = {'string': bytes_to_str(source),
             'safe': args.safe if(args.safe) else '/',
             'encoding': args.encoding,
             'errors': args.errors
             }
        res = handler_func(urllib.parse.quote,**a)

    elif(args.urld):
        a = {'string': bytes_to_str(source),
             'encoding': args.encoding,
             'errors': args.errors}

        res = handler_func(urllib.parse.unquote,**a)
    
    # Output the result
    if res is not None:
        if(args.output):
            try:
                # Write the reault to the specified output file 
                with open(args.output,'w') as f:
                    f.write(bytes_to_str(res))
                    f.close()
            except Exception as e:
                print(e)
        # Print the result to the console
        else:
            print(bytes_to_str(res))

if __name__ == '__main__':
    main()
