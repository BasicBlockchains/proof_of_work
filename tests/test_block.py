'''
We test the Block class and related functions
'''
import secrets
from hashlib import sha256

from .context import Block, calc_merkle_root, merkle_proof, utc_to_seconds, Decoder
from .helpers import random_hash, random_target, random_tx, random_mining_tx


def test_merkle_root():
    transactions = []
    for x in range(0, 2):
        transactions.append(random_tx())

    mining_tx = random_mining_tx()

    test_block = Block(prev_id='', target=secrets.randbits(256), nonce=secrets.randbits(64), timestamp=utc_to_seconds(),
                       mining_tx=mining_tx,
                       transactions=transactions)

    tx_ids = test_block.tx_ids
    calculated_merkle_root = calc_merkle_root(tx_ids)

    hash_ab = sha256((tx_ids[0] + tx_ids[1]).encode()).hexdigest()
    hash_cc = sha256((tx_ids[2] + tx_ids[2]).encode()).hexdigest()

    result_dict1 = merkle_proof(tx_ids[0], tx_ids, calculated_merkle_root)
    result_dict2 = merkle_proof(tx_ids[1], tx_ids, calculated_merkle_root)
    result_dict3 = merkle_proof(tx_ids[2], tx_ids, calculated_merkle_root)

    # 1st tx_id
    layer2_1 = result_dict1[0]
    layer1_1 = result_dict1[1]
    layer0_1 = result_dict1[2]

    assert layer2_1[2] == tx_ids[1]
    assert not layer2_1['is_left']
    assert layer1_1[1] == hash_cc
    assert not layer1_1['is_left']
    assert layer0_1[0] == test_block.merkle_root
    assert layer0_1['root_verified']

    # 2nd tx_id
    layer2_2 = result_dict2[0]
    layer1_2 = result_dict2[1]
    layer0_2 = result_dict2[2]

    assert layer2_2[2] == tx_ids[0]
    assert layer2_2['is_left']
    assert layer1_2[1] == hash_cc
    assert not layer1_2['is_left']
    assert layer0_2[0] == test_block.merkle_root
    assert layer0_2['root_verified']

    # 3rd tx_id
    layer2_3 = result_dict3[0]
    layer1_3 = result_dict3[1]
    layer0_3 = result_dict3[2]

    assert layer2_3[2] == tx_ids[2]
    assert not layer2_3['is_left']
    assert layer1_3[1] == hash_ab
    assert layer1_3['is_left']
    assert layer0_3[0] == test_block.merkle_root
    assert layer0_3['root_verified']


def test_block():
    # Decoder and Formatter
    d = Decoder()

    # Get header values
    prev_id = random_hash()
    target = random_target()
    nonce = secrets.randbits(64)
    timestamp = utc_to_seconds()

    # Get mining_tx
    mining_tx = random_mining_tx()

    # Get transactions
    transactions = []
    tx_num = secrets.randbits(4)
    for x in range(0, tx_num):
        transactions.append(random_tx())

    # Create Block
    block1 = Block(prev_id=prev_id, target=target, nonce=nonce, timestamp=timestamp, mining_tx=mining_tx,
                   transactions=transactions)
    raw_block = block1.raw_block
    raw_header = block1.raw_header
    # TESTING
    raw_block_transactions = block1.raw_transactions
    header = d.raw_block_header(raw_header)
    temp_mining_tx, temp_transactions = d.raw_block_transactions(raw_block_transactions)
    block2 = d.raw_block(raw_block)

    # Verify raw block
    assert block2.raw_block == raw_block

    # Verify mining_Tx
    assert temp_mining_tx.raw_tx == mining_tx.raw_tx

    # Verify UserTx
    for y in range(0, tx_num):
        assert transactions[y].raw_tx == temp_transactions[y].raw_tx

    # Verify dict values
    assert header.prev_id == prev_id
    assert header.merkle_root == block1.merkle_root
    assert header.nonce == nonce
    assert header.target == target
    assert header.timestamp == timestamp
