'''
Tests for header class
'''
from .context import Decoder
from .helpers import random_header


def test_raw_header():
    '''
    Verifies encoding/decoding of block header
    '''

    # Decoder
    d = Decoder()

    # Random header
    header = random_header()

    # Decode raw header
    raw_header = header.raw_header
    decoded_header = d.raw_block_header(raw_header)

    # Asserts
    assert decoded_header.id == header.id
    assert decoded_header.raw_header == raw_header
