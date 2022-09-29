'''
Testing the api - use local ip to avoid port forwarding
'''

from .context import Node, create_app, run_app, Formatter, DataBase, mine_a_block, MiningTransaction, Block, \
    utc_to_seconds, Decoder, UTXO_OUTPUT, UTXO_INPUT, Transaction, Wallet
from .helpers import random_unmined_block, create_node_gb, copy_node_gb
import threading
import logging
import json
import time
import os
from pathlib import Path

# --- CONSTANTS --- #
f = Formatter()
d = Decoder()


def test_endpoints():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_api/'
    else:
        dir_path = './tests/data/test_api/'
    file_name = 'test_endpoints.db'

    # Logging
    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('CRITICAL')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Create first node + api
    node1 = create_node_gb(
        Node(dir_path, file_name, logger=test_logger, local=True)
    )

    n1_thread = threading.Thread(target=run_app, daemon=True, args=(node1,))
    n1_thread.start()

    # Allow time to pass for api to get setup
    time.sleep(1)

    assert n1_thread.is_alive()
    assert node1.connect_to_network(node1.node)
    assert node1.is_connected

    # # Add block to node1

    mt = MiningTransaction(1, node1.mining_reward, 0, node1.wallet.address, 1)
    unmined_block = Block(node1.last_block.id, node1.target, 0, utc_to_seconds(), mt, [])
    mined_block = mine_a_block(unmined_block)
    # node1.add_block(mined_block)
    assert node1.add_block(mined_block)
    assert node1.height == 1

    # Create second node + api
    node2 = copy_node_gb(
        Node(dir_path, file_name, logger=test_logger, local=True), node1.blockchain.chain[0]
    )

    n2_thread = threading.Thread(target=run_app, daemon=True, args=(node2,))
    n2_thread.start()

    # Allow time to pass for api to get setup
    time.sleep(1)

    # Verify connect to network
    assert n2_thread.is_alive()
    assert node2.connect_to_network(node1.node)
    assert node2.is_connected

    # Verify that catchup ran
    assert node2.height == 1
    node2.blockchain.pop_block()
    assert node2.height == 0

    # Verify node lists
    assert node1.node in node2.node_list
    assert node1.node in node1.node_list
    assert node2.node in node1.node_list
    assert node2.node in node2.node_list
    assert len(node1.node_list) == len(node2.node_list) == 2

    # --- CHECK ENDPOINTS --- #

    # Check genesis
    assert node1.check_genesis(node2.node)
    assert node2.check_genesis(node1.node)

    # Get height
    assert node2.get_height(node1.node) == 1

    # Assert send block
    assert node1.send_raw_block_to_node(mined_block.raw_block, node2.node)
    assert node2.height == 1

    # Verify block
    assert node2.last_block.id == mined_block.id

    # Assert get indexed raw block
    assert node2.get_raw_block_from_node(node1.node, 0) == node2.blockchain.chain[0].raw_block
    assert node1.get_raw_block_from_node(node2.node) == node1.blockchain.chain[1].raw_block

    # Create new transaction
    last_block = node1.last_block
    tx_id = last_block.mining_tx.id
    tx_index = 0
    signature = node1.wallet.sign_transaction(tx_id)

    utxo_input = UTXO_INPUT(tx_id, tx_index, signature)
    utxo_output1 = UTXO_OUTPUT(node1.mining_reward // 2 - 1, node1.wallet.address)
    utxo_output2 = UTXO_OUTPUT(node1.mining_reward // 2 - 1, node2.wallet.address)
    new_tx = Transaction(inputs=[utxo_input], outputs=[utxo_output1, utxo_output2])
    assert node1.add_transaction(new_tx)
    assert node2.validated_transactions[0].id == new_tx.id

    # Check wallet functions
    assert node1.wallet.get_node_list(node2.node)
    assert node1.node in node1.wallet.node_list
    assert node2.node in node1.wallet.node_list

    # Verify disconnect
    node2.disconnect_from_network()
    assert node1.node_list == [node1.node]
    assert node2.node_list == []
    node1.disconnect_from_network()
    assert node1.node_list == []

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
