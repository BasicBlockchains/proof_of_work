'''
Tests for the transaction
'''
import secrets

from .context import UTXO_INPUT, UTXO_OUTPUT, Transaction, MiningTransaction, Wallet, Decoder
from .test_wallet import random_tx_id


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


def test_mining_tx():
    # Decoder
    d = Decoder()

    # Wallet for address
    w = Wallet()

    # Random mining values
    reward = secrets.randbits(32)
    height = secrets.randbits(64)
    fees = secrets.randbits(64)
    block_height = secrets.randbits(64)

    mining_tx = MiningTransaction(height, reward, fees, w.address, block_height)
    recovered_mining_tx = d.raw_mining_transaction(mining_tx.raw_tx)
    assert mining_tx.raw_tx == recovered_mining_tx.raw_tx
    assert mining_tx.id == recovered_mining_tx.id
