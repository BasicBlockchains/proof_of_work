'''
Tests for the Node class
'''
from src.bb_pow.data_structures.transactions import Transaction
from src.bb_pow.components.node import Node
import os
from src.bb_pow.data_format.timestamp import utc_to_seconds
import sqlite3
from src.bb_pow.components.wallet import Wallet
from src.bb_pow.data_structures.utxo import UTXO_OUTPUT, UTXO_INPUT
import werkzeug


def test_add_transaction():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_node/'
    else:
        dir_path = './tests/data/test_node/'
    file_name = 'test_add_transaction.db'

    # Create Node
    n = Node(dir_path, file_name)

    # Empty old blocks
    while n.height > 0:
        n.blockchain.pop_block()

    # Mine necessary Block
    start_time = utc_to_seconds()
    n.start_miner()
    while n.height < 1:
        pass
    print(f'Elapsed mining time in seconds: {utc_to_seconds() - start_time}', end='\r\n')
    n.stop_miner()

    # Check mining is off
    assert not n.is_mining

    # Modify block_height
    conn = sqlite3.connect(os.path.join(dir_path, file_name))
    c = conn.cursor()
    insert_string = """UPDATE utxo_pool SET block_height = 0"""
    c.execute(insert_string)
    conn.commit()
    conn.close()

    # UTXO_INPUT
    tx_id = n.last_block.mining_tx.id
    tx_index = 0
    signature = n.wallet.sign_transaction(tx_id)
    utxo_input = UTXO_INPUT(tx_id, tx_index, signature)

    # UTXO_OUTPUTS
    amount = n.mining_reward // 2
    new_address = Wallet().address
    utxo_output1 = UTXO_OUTPUT(amount=amount, address=new_address)
    utxo_output2 = UTXO_OUTPUT(amount=amount, address=n.wallet.address)

    # Transaction
    new_tx = Transaction(inputs=[utxo_input], outputs=[utxo_output1, utxo_output2])

    # Create Orphan transaction
    orphan_id = new_tx.id
    orphan_output_index = new_tx.outputs.index(utxo_output2)
    orphan_sig = n.wallet.sign_transaction(orphan_id)
    orphan_utxo_input = UTXO_INPUT(orphan_id, orphan_output_index, orphan_sig)

    orphan_utxo_output1 = UTXO_OUTPUT(amount=amount // 2, address=new_address)
    orphan_utxo_output2 = UTXO_OUTPUT(amount=amount // 2, address=n.wallet.address)

    orphan_tx = Transaction(inputs=[orphan_utxo_input], outputs=[orphan_utxo_output1, orphan_utxo_output2])

    # Add Transactions
    assert n.add_transaction(new_tx)
    assert n.add_transaction(orphan_tx)
    assert n.validated_transactions[0].raw_tx == new_tx.raw_tx
    assert n.orphaned_transactions[0].raw_tx == orphan_tx.raw_tx

    # Mine next Block
    current_height = n.height
    start_time = utc_to_seconds()
    n.start_miner()
    while n.height < current_height + 1:
        pass
    print(f'Elapsed mining time in seconds: {utc_to_seconds() - start_time}', end='\r\n')
    n.stop_miner()

    # Check mining is off
    assert not n.is_mining

    # Check tx got mined and orphan is validated
    assert n.orphaned_transactions == []
    assert n.validated_transactions[0].raw_tx == orphan_tx.raw_tx
    assert n.blockchain.find_block_by_tx_id(new_tx.id).raw_block == n.last_block.raw_block
