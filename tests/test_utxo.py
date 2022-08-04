'''
Tests for the UTXO class
'''
import secrets

from src.bb_pow.utxo import *
from .test_wallet import random_tx_id


def test_utxo():
    '''
    We generate random utxos and make sure their __repr__ values instantiate the same object
    '''

    # Utxo input
    w = Wallet()
    tx_id = random_tx_id()
    random_num = secrets.randbelow(100)
    signature = w.encode_signature(w.sign_transaction(tx_id))
    utxo_input = UTXO_INPUT(tx_id, random_num, signature)
    calc_input = UTXO_INPUT(utxo_input.tx_id, utxo_input.index, utxo_input.signature)
    assert utxo_input.id == calc_input.id

    # Utxo output
    amount = secrets.randbelow(100)
    block_height = secrets.randbelow(100)
    utxo_output = UTXO_OUTPUT(amount, w.address, block_height)
    calc_output = UTXO_OUTPUT(utxo_output.amount, utxo_output.address, utxo_output.block_height)
    assert utxo_output.id == calc_output.id
