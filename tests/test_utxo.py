'''
Tests for the UTXO class
'''

from .context import UTXO_INPUT, UTXO_OUTPUT, Decoder
from .helpers import random_hash, random_signature, random_index, random_amount, random_height, random_address


def test_utxo():
    '''
    We generate random utxos and make sure their __repr__ values instantiate the same object
    '''
    # Decoder
    d = Decoder()

    # Utxo input
    tx_id = random_hash()
    index = random_index()
    signature = random_signature(tx_id)
    utxo_input = UTXO_INPUT(tx_id, index, signature)

    # Recreated utxo from raw
    decoded_utxo_input = d.raw_utxo_input(utxo_input.raw_utxo)

    # Assertions
    assert utxo_input.raw_utxo == decoded_utxo_input.raw_utxo
    assert utxo_input.id == decoded_utxo_input.id

    # Utxo output
    amount = random_amount()
    address = random_address()
    block_height = random_height()
    utxo_output = UTXO_OUTPUT(amount, address, block_height)

    # Recreated utxo from raw
    decoded_utxo_output = d.raw_utxo_output(utxo_output.raw_utxo)

    # Assertions
    assert utxo_output.raw_utxo == decoded_utxo_output.raw_utxo
    assert utxo_output.id == decoded_utxo_output.id
