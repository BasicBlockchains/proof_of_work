'''
Tests for the UTXO class
'''
import secrets

from src.bb_pow.data_structures.utxo import UTXO_INPUT, UTXO_OUTPUT
from src.bb_pow.components.wallet import Wallet
from .test_wallet import random_tx_id
from src.bb_pow.data_format.decoder import Decoder


def test_utxo():
    '''
    We generate random utxos and make sure their __repr__ values instantiate the same object
    '''
    # Decoder
    d = Decoder()

    # Utxo input
    w = Wallet()
    tx_id = random_tx_id()
    random_num = secrets.randbelow(100)
    signature = w.sign_transaction(tx_id)
    utxo_input = UTXO_INPUT(tx_id, random_num, signature)

    # Recreated utxo from raw
    decoded_utxo_input = d.raw_utxo_input(utxo_input.raw_utxo)

    # Assertions
    assert utxo_input.raw_utxo == decoded_utxo_input.raw_utxo
    assert utxo_input.id == decoded_utxo_input.id

    # Utxo output
    amount = secrets.randbelow(100)
    block_height = secrets.randbelow(100)
    utxo_output = UTXO_OUTPUT(amount, w.address, block_height)

    # Recreated utxo from raw
    decoded_utxo_output = d.raw_utxo_output(utxo_output.raw_utxo)

    # Assertions
    assert utxo_output.raw_utxo == decoded_utxo_output.raw_utxo
    assert utxo_output.id == decoded_utxo_output.id
