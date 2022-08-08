'''
Tests for the transaction
'''
import secrets

from src.bb_pow.utxo import UTXO_INPUT, UTXO_OUTPUT
from src.bb_pow.transactions import Transaction
from src.bb_pow.wallet import Wallet
from .test_wallet import random_tx_id
from src.bb_pow.decoder import Decoder


def test_transaction():
    # Decoder
    d = Decoder()

    # Random utxo_input
    tx_id = random_tx_id()
    index = secrets.randbelow(100)
    w1 = Wallet()
    signature = w1.sign_transaction(tx_id)

    utxo_input = UTXO_INPUT(tx_id, index, signature)

    # Random utxo_output
    w2 = Wallet()
    amount = secrets.randbelow(100)
    address = w2.address
    block_height = secrets.randbelow(100)

    utxo_output = UTXO_OUTPUT(amount, address, block_height)

    # Transaction
    tx = Transaction(inputs=[utxo_input], outputs=[utxo_output])
    recovered_tx = d.raw_transaction(tx.raw_tx)

    # Assertions
    assert tx.id == recovered_tx.id
    assert tx.raw_tx == recovered_tx.raw_tx
