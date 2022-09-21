'''
Testing the api - use local ip to avoid port forwarding
'''

from .context import Node, create_app, run_app, Formatter, DataBase, mine_a_block, MiningTransaction, Block, \
    utc_to_seconds, Decoder
from .helpers import random_unmined_block
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
    test_logger.setLevel('ERROR')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Create first node + api
    node1 = Node(dir_path, file_name, logger=test_logger)
    n1_thread = threading.Thread(target=run_app, daemon=True, args=(node1,))
    n1_thread.start()

    # Allow time to pass for api to get setup
    time.sleep(1)

    assert n1_thread.is_alive()
    assert node1.connect_to_network(node1.local_node, local=True)
    assert node1.is_connected

    # Add block to node1
    node1.blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20)
    mt = MiningTransaction(1, node1.mining_reward, 0, node1.wallet.address, 1 + Formatter.MINING_DELAY)
    unmined_block = Block(node1.last_block.id, node1.target, 0, utc_to_seconds(), mt, [])
    mined_block = mine_a_block(unmined_block)
    assert node1.add_block(mined_block, gossip=False)
    assert node1.height == 1

    # Create second node + api
    node2 = Node(dir_path, file_name, logger=test_logger)
    node2.blockchain.target = node1.blockchain.target

    n2_thread = threading.Thread(target=run_app, daemon=True, args=(node2,))
    n2_thread.start()

    # Allow time to pass for api to get setup
    time.sleep(1)

    # Verify connect to network
    assert n2_thread.is_alive()
    assert node2.connect_to_network(node1.local_node, local=True)
    assert node2.is_connected

    # Verify that catchup ran
    assert node2.height == 1
    node2.blockchain.pop_block()
    assert node2.height == 0

    # Verify node lists
    assert node1.local_node in node2.node_list
    assert node1.local_node in node1.node_list
    assert node2.local_node in node1.node_list
    assert node2.local_node in node2.node_list
    assert len(node1.node_list) == len(node2.node_list) == 2

    # --- CHECK ENDPOINTS --- #

    # Check genesis
    assert node1.check_genesis(node2.local_node)
    assert node2.check_genesis(node1.local_node)

    # Get height
    assert node2.get_height(node1.local_node) == 1

    # Assert send block
    assert node1.send_raw_block_to_node(mined_block.raw_block, node2.local_node)
    assert node2.height == 1

    # Assert get indexed raw block
    assert node2.get_raw_block_from_node(node1.local_node, 0) == node2.blockchain.chain[0].raw_block
    assert node1.get_raw_block_from_node(node2.local_node) == node1.blockchain.chain[1].raw_block

    # Verify disconnect
    node2.disconnect_from_network(local=True)
    assert node1.node_list == [node1.local_node]
    assert node2.node_list == []
    node1.disconnect_from_network(local=True)
    assert node1.node_list == []

    # print(node1.node)
    # print(node2.node)

    # Cleanup nodes
    while node1.height > 0:
        node1.blockchain.pop_block()
    while node2.height > 0:
        node2.blockchain.pop_block()
