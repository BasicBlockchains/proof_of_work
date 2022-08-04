'''
Tests for the transaction
'''
import secrets

from src.bb_pow.utxo import UTXO_INPUT, UTXO_OUTPUT
from src.bb_pow.transactions import Transaction
from src.bb_pow.wallet import Wallet
from .test_wallet import random_tx_id


def test_transaction():
    # Random utxo_input
    tx_id = random_tx_id()
    index = secrets.randbelow(100)
    w1 = Wallet()
    signature = w1.encode_signature(w1.sign_transaction(tx_id))

    utxo_input = UTXO_INPUT(tx_id, index, signature)

    # Random utxo_output
    w2 = Wallet()
    amount = secrets.randbelow(100)
    address = w2.address
    block_height = secrets.randbelow(100)

    utxo_output = UTXO_OUTPUT(amount, address, block_height)

    # Transaction
    tx = Transaction(inputs=[utxo_input], outputs=[utxo_output])
    calc_tx = Transaction(inputs=tx.inputs, outputs=tx.outputs)
    assert tx.id == calc_tx.id
