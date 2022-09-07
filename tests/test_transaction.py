'''
Tests for the transaction
'''

from .context import Decoder
from .helpers import random_tx, random_mining_tx


def test_transaction():
    '''
    Verify raw_tx to Transaction is properly decoded
    '''
    # Decoder
    d = Decoder()

    # Random transaction
    text_tx = random_tx()

    # Decode transaction
    raw_tx = text_tx.raw_tx
    decoded_tx = d.raw_transaction(raw_tx)

    # Asserts
    assert decoded_tx.id == text_tx.id
    assert decoded_tx.raw_tx == raw_tx


def test_mining_tx():
    '''
    Verify raw_mining_tx to MiningTransaction is properly decoded
    '''

    # Decoder
    d = Decoder()

    # Random mining tx
    mining_tx = random_mining_tx()

    # Decode mining transaction
    raw_mining_tx = mining_tx.raw_tx
    decoded_mining_tx = d.raw_mining_transaction(raw_mining_tx)

    # Asserts
    assert decoded_mining_tx.id == mining_tx.id
    assert decoded_mining_tx.raw_tx == raw_mining_tx
