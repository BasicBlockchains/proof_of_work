'''
Testing the blockchain
'''
import logging
import os
import json
import secrets
from pathlib import Path

from .context import Block, Blockchain, DataBase, Decoder, Formatter, MiningTransaction, Transaction, \
    utc_to_seconds, UTXO_INPUT, UTXO_OUTPUT, mine_a_block
from .helpers import random_unmined_block, random_address, address_from_private_key

# --- Constants --- #
d = Decoder()
f = Formatter()


def test_add_pop_block():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_blockchain/'
    else:
        dir_path = './tests/data/test_blockchain/'
    file_name = 'test_add_pop_block.db'

    # Start with empty db
    db = DataBase(dir_path, file_name)
    db.wipe_db()
    db.create_db()

    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('WARNING')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Blockchain
    test_chain = Blockchain(dir_path, file_name, logger=test_logger)

    # Verify db only has genesis block
    assert test_chain.chain_db.get_height()['height'] == 0

    # Modify target for testing
    test_chain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x1f)

    # Fix address
    private_key = secrets.randbits(f.HASH_CHARS * 4)
    fixed_address = address_from_private_key(private_key)

    # Create first block
    mining_tx1 = MiningTransaction(1, test_chain.mining_reward, 0, fixed_address, f.MINING_DELAY + 1)
    unmined_block1 = Block(test_chain.last_block.id, test_chain.target, 0, utc_to_seconds(), mining_tx1, [])
    mined_block1 = mine_a_block(unmined_block1)

    # Add first block
    assert test_chain.add_block(mined_block1)

    # Create transaction
    # inputs
    input_utxo = UTXO_INPUT(
        tx_id=mining_tx1.id,
        index=0,
        signature=f.signature(private_key, mining_tx1.id)
    )
    # outputs
    output_utxo1 = UTXO_OUTPUT(amount=test_chain.mining_reward // 2 - 1, address=random_address())
    output_utxo2 = UTXO_OUTPUT(amount=test_chain.mining_reward // 2 - 1, address=fixed_address)

    # tx
    new_tx = Transaction([input_utxo], [output_utxo1, output_utxo2])

    block_fees = test_chain.mining_reward - 2 * (test_chain.mining_reward // 2 - 1)

    # Create next block
    mining_tx2 = MiningTransaction(2, test_chain.mining_reward, block_fees, fixed_address,
                                   f.MINING_DELAY + 2)
    unmined_block2 = Block(test_chain.last_block.id, test_chain.target, 0, utc_to_seconds(), mining_tx2, [new_tx])
    mined_block2 = mine_a_block(unmined_block2)

    # Add next block
    assert test_chain.add_block(mined_block2)

    # Verify tx is in chain
    assert test_chain.find_block_by_tx_id(new_tx.id).id == mined_block2.id

    # Pop Block
    assert test_chain.pop_block()

    # Make sure mining_tx from 2nd block is gone
    assert test_chain.chain_db.get_utxo(mining_tx2.id, 0) == {}

    # Make sure constructed tx isn't found
    assert test_chain.find_block_by_tx_id(new_tx.id) is None

    # Pop Block
    assert test_chain.pop_block()

    # Make sure mining_tx from 1st block is gone
    assert test_chain.chain_db.get_utxo(mining_tx1.id, 0) == {}

    # Make sure we can't pop the genesis block
    assert not test_chain.pop_block()


def test_fork():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_blockchain/'
    else:
        dir_path = './tests/data/test_blockchain/'
    file_name = 'test_fork.db'

    # Start with empty db
    db = DataBase(dir_path, file_name)
    db.wipe_db()
    db.create_db()

    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('ERROR')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Blockchain
    test_chain = Blockchain(dir_path, file_name, logger=test_logger)
    genesis_block = test_chain.chain[0]

    # Modify target for testing
    test_chain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x1f)

    # Verify chain is only genesis block
    assert test_chain.chain[0].id == genesis_block.id

    # Create first block
    unmined_block1 = random_unmined_block(test_chain.last_block.id, 1, test_chain.mining_reward,
                                          test_chain.target)
    mined_block1 = mine_a_block(unmined_block1)

    # Add block
    assert test_chain.add_block(mined_block1)
    assert test_chain.chain[1].id == mined_block1.id

    # Create fork block
    unmined_fork = random_unmined_block(test_chain.chain[0].id, 1, test_chain.mining_reward, test_chain.target)
    mined_fork = mine_a_block(unmined_fork)

    # Add block - should end up in forks
    assert not test_chain.add_block(mined_fork)
    assert test_chain.forks == [{1: mined_fork.raw_block}]

    # Add block again - forks should remain the same
    assert not test_chain.add_block(mined_fork)
    assert test_chain.forks == [{1: mined_fork.raw_block}]

    # Create next block for fork
    unmined_fork2 = random_unmined_block(mined_fork.id, 2, test_chain.mining_reward,
                                         test_chain.target)
    mined_fork2 = mine_a_block(unmined_fork2)

    # Asserts - mined_fork2 should get added to chain, mined_fork should get removed from forks and added to chain
    # mined_block1 should get added to forks
    assert test_chain.add_block(mined_fork2)
    assert test_chain.forks == [{1: mined_block1.raw_block}]
    assert test_chain.chain[1].id == mined_fork.id
    assert test_chain.chain[2].id == mined_fork2.id

    # Create second block
    unmined_block2 = random_unmined_block(mined_block1.id, 2, test_chain.mining_reward, test_chain.target)
    mined_block2 = mine_a_block(unmined_block2)

    # Asserts - should add block to forks
    assert not test_chain.add_block(mined_block2)
    assert test_chain.forks == [{1: mined_block1.raw_block}, {2: mined_block2.raw_block}]

    # Create third block
    unmined_block3 = random_unmined_block(mined_block2.id, 3, test_chain.mining_reward, test_chain.target)
    mined_block3 = mine_a_block(unmined_block3)

    # Asserts - mined_block3 gets added, mined_block2 and mined_block1 get removed from forks and added
    # Asserts - mined_fork and mined_fork2 and in forks
    assert test_chain.add_block(mined_block3)
    assert test_chain.forks == [{1: mined_fork.raw_block}, {2: mined_fork2.raw_block}]
    assert test_chain.chain[1].id == mined_block1.id
    assert test_chain.chain[2].id == mined_block2.id
    assert test_chain.chain[3].id == mined_block3.id

    # Create third malformed fork
    unmined_malformed_fork = random_unmined_block(mined_fork2.id, 4, test_chain.mining_reward, test_chain.target + 1)
    mined_malformed_fork = mine_a_block(unmined_malformed_fork)
    assert not test_chain.add_block(mined_malformed_fork)
    assert test_chain.forks == [{1: mined_fork.raw_block}, {2: mined_fork2.raw_block}]

    # Finally create third valid fork
    unmined_fork3 = random_unmined_block(mined_fork2.id, 3, test_chain.mining_reward, test_chain.target)
    mined_fork3 = mine_a_block(unmined_fork3)
    assert not test_chain.add_block(mined_fork3)
    assert test_chain.forks == [{1: mined_fork.raw_block}, {2: mined_fork2.raw_block}, {3: mined_fork3.raw_block}]

    # Final recursive test
    unmined_fork4 = random_unmined_block(mined_fork3.id, 4, test_chain.mining_reward, test_chain.target)
    mined_fork4 = mine_a_block(unmined_fork4)
    assert test_chain.add_block(mined_fork4)
    assert test_chain.forks == [{1: mined_block1.raw_block}, {2: mined_block2.raw_block}, {3: mined_block3.raw_block}]


def test_memchain():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_blockchain/'
    else:
        dir_path = './tests/data/test_blockchain/'
    file_name = 'test_memchain.db'

    # Start with empty db
    db = DataBase(dir_path, file_name)
    db.wipe_db()
    db.create_db()

    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('WARNING')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    # Blockchain
    test_chain = Blockchain(dir_path, file_name, logger=test_logger)
    genesis_block = test_chain.chain[0]

    # Modify target for testing
    test_chain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20)

    # Modify heartbeat for testing
    test_chain.heartbeat = 5

    # Mine heartbeat + x blocks, where x in (2,3)
    block_list_ids = [genesis_block.id]
    while test_chain.height < test_chain.heartbeat + 2:
        # Create first block
        next_unmined_block = random_unmined_block(test_chain.last_block.id, test_chain.height + 1,
                                                  test_chain.mining_reward, test_chain.target)
        next_block = mine_a_block(next_unmined_block)
        block_list_ids.append(next_block.id)
        assert test_chain.add_block(next_block)

    # # Test memchain
    assert test_chain.height == test_chain.heartbeat + 2
    assert len(test_chain.chain) == test_chain.heartbeat + 1
    assert test_chain.last_block.id == block_list_ids[test_chain.height]
    assert test_chain.chain[0].id == genesis_block.id == block_list_ids[0]
    assert test_chain.chain[1].id == block_list_ids[test_chain.height + 1 - test_chain.heartbeat]

    # Test pop block
    assert test_chain.pop_block()

    # Test memchain
    assert test_chain.height == test_chain.heartbeat + 1
    assert len(test_chain.chain) == test_chain.heartbeat + 1
    assert test_chain.last_block.id == block_list_ids[test_chain.height]
    assert test_chain.chain[0].id == genesis_block.id == block_list_ids[0]
    assert test_chain.chain[1].id == block_list_ids[test_chain.height - test_chain.heartbeat]

    # Test pop block
    assert test_chain.pop_block()

    # Test memchain removing blocks as expected
    assert test_chain.height == test_chain.heartbeat
    assert len(test_chain.chain) == test_chain.heartbeat
    assert test_chain.last_block.id == block_list_ids[test_chain.height]
    assert test_chain.chain[0].id == genesis_block.id == block_list_ids[0]
    assert test_chain.chain[1].id == block_list_ids[1]
