'''
Tests for header class
'''
import secrets
from .test_wallet import random_tx_id
from .test_block import get_random_target
from .context import Decoder, utc_to_seconds, Header


def test_raw_header():
    # Decoder
    d = Decoder()

    # Random header values
    prev_id = random_tx_id()
    merkle_root = random_tx_id()
    target = get_random_target()
    nonce = secrets.randbelow(pow(10, 6))
    timestamp = utc_to_seconds()

    header = Header(prev_id, merkle_root, target, nonce, timestamp)
    constructed_header = d.raw_block_header(header.raw_header)
    assert constructed_header.id == header.id
