'''
Tests for the Node class
'''
import logging
import os
from pathlib import Path
import threading
import time

from .context import Node, Wallet, Block, utc_to_seconds, Transaction, MiningTransaction, mine_a_block, UTXO_INPUT, \
    UTXO_OUTPUT, Formatter, DataBase, run_app

# --- CONSTANTS --- #
f = Formatter()


def create_test_node_block(node: Node):
    # Get as many validated transactions that will fit in the Block
    bit_size = 0
    node.block_transactions = []
    while bit_size <= node.f.MAXIMUM_BIT_SIZE and node.validated_transactions != []:
        node.block_transactions.append(node.validated_transactions.pop(0))  # Add first validated transaction
        bit_size += len(node.block_transactions[-1].raw_tx) * 4  # Increase bit_size by number of hex chars * 4

    # Get block fees
    block_fees = 0
    for tx in node.block_transactions:
        block_fees += node.get_fees(tx)

    # Create Mining Transaction
    mining_tx = MiningTransaction(node.height + 1, node.mining_reward, block_fees, node.wallet.address, node.height + 1)

    # Return unmined block
    return Block(node.last_block.id, node.target, 0, utc_to_seconds(), mining_tx, node.block_transactions)


def test_add_transaction():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_node/'
    else:
        dir_path = './tests/data/test_node/'
    file_name = 'test_add_transaction.db'

    # Start with empty db
    db = DataBase(dir_path, file_name)
    db.wipe_db()
    db.create_db()

    # Logging
    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('CRITICAL')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Create Node
    n = Node(dir_path, file_name, logger=test_logger)

    # Set connected flag
    n.is_connected = True

    # CHANGE MINING DELAY
    n.blockchain.f.MINING_DELAY = 0

    # CHANGE blockchain target
    n.blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x1f)

    # Mine necessary Block
    block1 = create_test_node_block(n)
    mined_block1 = mine_a_block(block1)
    assert n.add_block(mined_block1)

    # UTXO_INPUT
    tx_id = n.last_block.mining_tx.id
    tx_index = 0
    signature = n.wallet.sign_transaction(tx_id)
    utxo_input = UTXO_INPUT(tx_id, tx_index, signature)

    # UTXO_OUTPUTS
    amount = n.mining_reward // 2
    new_address = Wallet(logger=test_logger, save=False).address
    utxo_output1 = UTXO_OUTPUT(amount=amount - 1, address=new_address)
    utxo_output2 = UTXO_OUTPUT(amount=amount - 1, address=n.wallet.address)

    # Transaction
    new_tx = Transaction(inputs=[utxo_input], outputs=[utxo_output1, utxo_output2])

    # Create Orphan transaction
    orphan_id = new_tx.id
    orphan_output_index = new_tx.outputs.index(utxo_output2)
    orphan_sig = n.wallet.sign_transaction(orphan_id)
    orphan_utxo_input = UTXO_INPUT(orphan_id, orphan_output_index, orphan_sig)

    orphan_utxo_output1 = UTXO_OUTPUT(amount=amount // 2 - 1, address=new_address)
    orphan_utxo_output2 = UTXO_OUTPUT(amount=amount // 2 - 1, address=n.wallet.address)

    orphan_tx = Transaction(inputs=[orphan_utxo_input], outputs=[orphan_utxo_output1, orphan_utxo_output2])

    # Add Transactions
    assert n.add_transaction(new_tx)
    assert n.add_transaction(orphan_tx)
    assert n.validated_transactions[0].raw_tx == new_tx.raw_tx
    assert n.orphaned_transactions[0].raw_tx == orphan_tx.raw_tx

    # Mine next Block
    block2 = n.create_next_block()
    mined_block2 = mine_a_block(block2)
    assert n.add_block(mined_block2)

    # Check tx got mined and orphan is validated
    assert n.orphaned_transactions == []
    assert n.validated_transactions[0].raw_tx == orphan_tx.raw_tx
    assert n.blockchain.find_block_by_tx_id(new_tx.id).raw_block == n.last_block.raw_block

    # Empty blocks for next time
    while n.height > 0:
        n.blockchain.pop_block()


def test_catchup_to_network():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_node/'
    else:
        dir_path = './tests/data/test_node/'
    file_name = 'test_catchup_to_network.db'

    # Logging
    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('ERROR')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Create first node + api
    node1 = Node(dir_path, file_name, logger=test_logger, local=True)
    n1_thread = threading.Thread(target=run_app, daemon=True, args=(node1,))
    n1_thread.start()

    # Allow time to pass for api to get setup
    time.sleep(1)

    assert n1_thread.is_alive()
    assert node1.connect_to_network(node1.node)
    assert node1.is_connected

    # # Add block to node1
    node1.blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20)
    node1.blockchain.f.MINING_DELAY = 0
    node1.f.HEARTBEAT = 5

    # Create 12 blocks
    node1.start_miner()
    while node1.height < 10:
        pass
    node1.stop_miner()

    assert node1.height >= 10

    # Create 2nd node
    # Create second node + api
    node2 = Node(dir_path, file_name, logger=test_logger, local=True)
    node2.blockchain.target = node1.blockchain.target
    node2.blockchain.f.MINING_DELAY = 0
    node2.f.HEARTBEAT = 5

    n2_thread = threading.Thread(target=run_app, daemon=True, args=(node2,))
    n2_thread.start()

    # Allow time to pass for api to get setup
    time.sleep(1)

    node2.connect_to_network(node1.node)
    assert node2.height == node1.height

    # Cleanup nodes
    while node1.height > 0:
        node1.blockchain.pop_block()
    while node2.height > 0:
        node2.blockchain.pop_block()

    # Verify cleanup

    assert node1.height == 0
    assert node1.blockchain.chain_db.get_height()['height'] == 0
    assert node2.height == 0
    assert node2.blockchain.chain_db.get_height()['height'] == 0
