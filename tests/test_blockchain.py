'''
Testing the blockchain
'''
import os

from src.bb_pow.block import Block
from src.bb_pow.blockchain import Blockchain
from src.bb_pow.decoder import Decoder
from src.bb_pow.formatter import Formatter
from src.bb_pow.miner import Miner
from src.bb_pow.timestamp import utc_to_seconds
from src.bb_pow.transactions import MiningTransaction, Transaction
from src.bb_pow.utxo import UTXO_OUTPUT, UTXO_INPUT
from src.bb_pow.wallet import Wallet


# Helpers
def create_unmined_block(prev_id: id, height: int, reward: int, target: int):
    mining_tx = MiningTransaction(height, reward, 0, Wallet().address)
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
#     d = Decoder()
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
#
#     mining_tx = MiningTransaction(height, reward, block_fees, address)
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
#     miner.stop_mining()
#
#     # Add Block
#     assert test_chain.add_block(mined_block)
#
#     ##Add User Transaction
#
#     # Craft MiningTx again
#     mining_tx2 = MiningTransaction(height + 1, reward, block_fees, address)
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
    d = Decoder()

    # Blockchain
    test_chain = Blockchain(dir_path, file_name)
    while test_chain.height != 0:
        test_chain.pop_block()

    # Create miner
    miner = Miner()

    # Create Wallets
    w1 = Wallet()
    w2 = Wallet()

    # Create first block
    unmined_block1 = create_unmined_block(test_chain.last_block.id, 1, test_chain.mining_reward,
                                          test_chain.target)
    mined_block1 = miner.mine_block(unmined_block1)
    assert test_chain.add_block(mined_block1)

    # Create fork block
    unmined_fork = create_unmined_block(test_chain.chain[0].id, 1, test_chain.mining_reward, test_chain.target)
    mined_fork = miner.mine_block(unmined_fork)

    assert not test_chain.add_block(mined_fork)
    assert test_chain.forks == [{1: mined_fork}]

    # Create next block for fork
    unmined_fork2 = create_unmined_block(mined_fork.id, 2, test_chain.mining_reward,
                                         test_chain.target)
    mined_fork2 = miner.mine_block(unmined_fork2)

    assert test_chain.add_block(mined_fork2)
    assert test_chain.forks == [{1: mined_block1}]
    assert test_chain.chain[1].id == mined_fork.id

    # Create second block
    unmined_block2 = create_unmined_block(mined_block1.id, 2, test_chain.mining_reward, test_chain.target)
    mined_block2 = miner.mine_block(unmined_block2)
    assert not test_chain.add_block(mined_block2)
    assert test_chain.forks == [{1: mined_block1}, {2: mined_block2}]

    # Create third block
    unmined_block3 = create_unmined_block(mined_block2.id, 3, test_chain.mining_reward, test_chain.target)
    mined_block3 = miner.mine_block(unmined_block3)
    assert test_chain.add_block(mined_block3)
    assert test_chain.forks == [{1: mined_fork}, {2: mined_fork2}]

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