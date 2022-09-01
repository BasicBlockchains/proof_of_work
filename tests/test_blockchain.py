'''
Testing the blockchain
'''
import os
import secrets
import json
from .context import Block, Blockchain, Decoder, Formatter, Miner, utc_to_seconds, MiningTransaction, Transaction, \
    Wallet, UTXO_INPUT, UTXO_OUTPUT


# Helpers
def create_unmined_block(prev_id: id, height: int, reward: int, target: int):
    mining_tx = MiningTransaction(height, reward, 0, Wallet(seed=secrets.randbits(256)).address,
                                  height + Formatter.MINING_DELAY)
    return Block(prev_id, target, 0, utc_to_seconds(), mining_tx, [])


# def test_add_pop_block():
#     # Create db with path in tests directory
#     current_path = os.getcwd()
#     if '/tests' in current_path:
#         dir_path = current_path + '/data/test_blockchain/'
#     else:
#         dir_path = './tests/data/test_blockchain/'
#     file_name = 'test_add_pop_block.db'
#
#     # Formatter/Decoder
#     f = Formatter()
#
#     # Modify formatted exponent for testing
#     f.STARTING_TARGET_EXPONENT = 0x1f
#
#     # Blockchain
#     test_chain = Blockchain(dir_path, file_name)
#
#     # Create miner
#     miner = Miner()
#
#     # Create Wallets
#     w1 = Wallet()
#     w2 = Wallet()
#
#     # Craft MiningTx
#     height = test_chain.height + 1
#     reward = test_chain.mining_reward
#     block_fees = 0
#     address = w1.address
#     block_height = height + f.MINING_DELAY
#
#     mining_tx = MiningTransaction(height, reward, block_fees, address, block_height)
#
#     # Last block
#     last_block = test_chain.last_block
#
#     # Craft unmined Block
#     prev_id = last_block.id
#     target = test_chain.target
#     nonce = 0
#     timestamp = utc_to_seconds()
#     unmined_block = Block(prev_id, target=target, nonce=nonce, timestamp=timestamp,
#                           mining_tx=mining_tx, transactions=[])
#
#     # Mine Block
#     mined_block = miner.mine_block(unmined_block)
#
#     # Add Block
#     assert test_chain.add_block(mined_block)
#
#     ##Add User Transaction
#
#     # Craft MiningTx again
#     mining_tx2 = MiningTransaction(height + 1, reward, block_fees, address, block_height + 1)
#
#     # Craft Transaction
#     new_address = w2.address
#     signature = f.signature(w1.private_key, mining_tx.id)
#
#     input_utxo = UTXO_INPUT(mining_tx.id, 0, signature)
#
#     output_utxo1 = UTXO_OUTPUT(amount=test_chain.mining_reward // 2, address=new_address)
#     output_utxo2 = UTXO_OUTPUT(amount=test_chain.mining_reward // 2, address=address)
#
#     new_tx = Transaction(inputs=[input_utxo], outputs=[output_utxo1, output_utxo2])
#
#     # Next block
#     unmined_next_block = Block(prev_id=mined_block.id, target=target, nonce=nonce, timestamp=utc_to_seconds(),
#                                mining_tx=mining_tx2, transactions=[new_tx])
#     mined_next_block = miner.mine_block(unmined_next_block)
#
#     # Add next block
#     assert test_chain.add_block(mined_next_block)
#
#     # Pop Block
#     assert test_chain.pop_block()
#
#     # Make sure mining_tx from 2nd block is gone
#     assert test_chain.chain_db.get_utxo(mining_tx2.id, 0) == {}
#
#     # Pop Block
#     assert test_chain.pop_block()
#
#     # Make sure mining_tx from 1st block is gone
#     assert test_chain.chain_db.get_utxo(mining_tx.id, 0) == {}
#
#     # Make sure we can't pop the genesis block
#     assert not test_chain.pop_block()


def test_fork():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_blockchain/'
    else:
        dir_path = './tests/data/test_blockchain/'
    file_name = 'test_fork.db'

    # Formatter/Decoder
    f = Formatter()

    # Blockchain
    test_chain = Blockchain(dir_path, file_name)
    while test_chain.height != 0:
        test_chain.pop_block()

    # Genesis Block
    gb = test_chain.create_genesis_block()

    # Modify target for testing
    test_chain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x1f)

    # Create miner
    miner = Miner()

    # Verify chain is only genesis block
    assert test_chain.chain[0].id == gb.id

    # Create first block
    unmined_block1 = create_unmined_block(test_chain.last_block.id, 1, test_chain.mining_reward,
                                          test_chain.target)
    mined_block1 = miner.mine_block(unmined_block1)

    # Add block
    assert test_chain.add_block(mined_block1)
    assert test_chain.chain[1].id == mined_block1.id

    # Create fork block
    unmined_fork = create_unmined_block(test_chain.chain[0].id, 1, test_chain.mining_reward, test_chain.target)
    mined_fork = miner.mine_block(unmined_fork)

    # Add block - should end up in forks
    assert not test_chain.add_block(mined_fork)
    assert test_chain.forks == [{1: mined_fork}]

    # Create next block for fork
    unmined_fork2 = create_unmined_block(mined_fork.id, 2, test_chain.mining_reward,
                                         test_chain.target)
    mined_fork2 = miner.mine_block(unmined_fork2)

    # Asserts - mined_fork2 should get added to chain, mined_fork should get removed from forks and added to chain
    # mined_block1 should get added to forks
    assert test_chain.add_block(mined_fork2)
    assert test_chain.forks == [{1: mined_block1}]
    assert test_chain.chain[1].id == mined_fork.id
    assert test_chain.chain[2].id == mined_fork2.id

    # Create second block
    unmined_block2 = create_unmined_block(mined_block1.id, 2, test_chain.mining_reward, test_chain.target)
    mined_block2 = miner.mine_block(unmined_block2)

    # Asserts - should add block to forks
    assert not test_chain.add_block(mined_block2)
    assert test_chain.forks == [{1: mined_block1}, {2: mined_block2}]

    # Create third block
    unmined_block3 = create_unmined_block(mined_block2.id, 3, test_chain.mining_reward, test_chain.target)
    mined_block3 = miner.mine_block(unmined_block3)

    # Asserts - mined_block3 gets added, mined_block2 and mined_block1 get removed from forks and added
    # Asserts - mined_fork and mined_fork2 and in forks
    assert test_chain.add_block(mined_block3)
    assert test_chain.forks == [{1: mined_fork}, {2: mined_fork2}]
    assert test_chain.chain[1].id == mined_block1.id
    assert test_chain.chain[2].id == mined_block2.id
    assert test_chain.chain[3].id == mined_block3.id

    # Create third malformed fork
    unmined_malformed_fork = create_unmined_block(mined_fork2.id, 4, test_chain.mining_reward, test_chain.target + 1)
    mined_malformed_fork = miner.mine_block(unmined_malformed_fork)
    assert not test_chain.add_block(mined_malformed_fork)
    assert test_chain.forks == [{1: mined_fork}, {2: mined_fork2}]

    # Finally create third valid fork
    unmined_fork3 = create_unmined_block(mined_fork2.id, 3, test_chain.mining_reward, test_chain.target)
    mined_fork3 = miner.mine_block(unmined_fork3)
    assert not test_chain.add_block(mined_fork3)
    assert test_chain.forks == [{1: mined_fork}, {2: mined_fork2}, {3: mined_fork3}]

    # Final recursive test
    unmined_fork4 = create_unmined_block(mined_fork3.id, 4, test_chain.mining_reward, test_chain.target)
    mined_fork4 = miner.mine_block(unmined_fork4)
    assert test_chain.add_block(mined_fork4)
    assert test_chain.forks == [{1: mined_block1}, {2: mined_block2}, {3: mined_block3}]
