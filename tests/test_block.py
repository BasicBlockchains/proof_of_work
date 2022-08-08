'''
We test the Block class and related functions
'''
import secrets
from hashlib import sha256

from src.bb_pow.block import Block, calc_merkle_root, merkle_proof
from src.bb_pow.timestamp import utc_to_seconds
from src.bb_pow.transactions import Transaction
from src.bb_pow.utxo import UTXO_INPUT, UTXO_OUTPUT
from src.bb_pow.wallet import Wallet

from src.bb_pow.decoder import Decoder
from src.bb_pow.formatter import Formatter

from .test_wallet import random_tx_id


# ---Helpers---#
def get_random_utxo_input():
    # Id and index
    tx_id = random_tx_id()
    index = secrets.randbits(4)
    wallet = Wallet()

    # Signature
    signature = wallet.sign_transaction(tx_id)

    # UTXO
    return UTXO_INPUT(tx_id, index, signature)


def get_random_utxo_output():
    # Wallet

    # Random values
    amount = secrets.randbits(64)
    address = Wallet().address
    height = secrets.randbits(64)

    # UTXO
    return UTXO_OUTPUT(amount=amount, address=address, block_height=height)


def get_random_transaction():
    input_count = secrets.randbits(4)
    output_count = secrets.randbits(4)

    inputs = []
    for x in range(0, input_count):
        inputs.append(get_random_utxo_input())

    outputs = []
    for y in range(0, output_count):
        outputs.append(get_random_utxo_output())

    return Transaction(inputs=inputs, outputs=outputs)


def get_random_target():
    random_coeff = secrets.randbits(24)
    random_exp = 0
    while random_exp < 4:
        random_exp = secrets.randbits(8)
    return Formatter().target_from_parts(random_coeff, random_exp)


def test_merkle_root():
    transactions = []
    for x in range(3):
        transactions.append(get_random_transaction())

    test_block = Block(prev_id='', target=0, nonce=0, timestamp=utc_to_seconds(), transactions=transactions)

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
    assert layer2_1['is_left'] == False
    assert layer1_1[1] == hash_cc
    assert layer1_1['is_left'] == False
    assert layer0_1[0] == test_block.merkle_root
    assert layer0_1['root_verified'] == True

    # 2nd tx_id
    layer2_2 = result_dict2[0]
    layer1_2 = result_dict2[1]
    layer0_2 = result_dict2[2]

    assert layer2_2[2] == tx_ids[0]
    assert layer2_2['is_left'] == True
    assert layer1_2[1] == hash_cc
    assert layer1_2['is_left'] == False
    assert layer0_2[0] == test_block.merkle_root
    assert layer0_2['root_verified'] == True

    # 3rd tx_id
    layer2_3 = result_dict3[0]
    layer1_3 = result_dict3[1]
    layer0_3 = result_dict3[2]

    assert layer2_3[2] == tx_ids[2]
    assert layer2_3['is_left'] == False
    assert layer1_3[1] == hash_ab
    assert layer1_3['is_left'] == True
    assert layer0_3[0] == test_block.merkle_root
    assert layer0_3['root_verified'] == True


def test_block():
    # Decoder and Formatter
    d = Decoder()
    f = Formatter()

    transactions = []
    random_length = 0
    while random_length < 1:
        random_length = secrets.randbits(4)
    for x in range(random_length):
        transactions.append(get_random_transaction())

    prev_id = random_tx_id()
    target = get_random_target()
    nonce = secrets.randbits(4 * f.NONCE_CHARS)
    timestamp = utc_to_seconds()

    test_block = Block(prev_id, target, nonce, timestamp, transactions)
    decoded_block = d.raw_block(test_block.raw_block)

    # Assertions
    assert test_block.raw_headers == decoded_block.raw_headers
    assert test_block.raw_transactions == decoded_block.raw_transactions
    assert test_block.raw_block == decoded_block.raw_block
    assert test_block.id == decoded_block.id

    # Verify values
    header_dict = d.raw_block_headers(test_block.raw_headers)
    assert header_dict['prev_id'] == prev_id
    assert header_dict['merkle_root'] == test_block.merkle_root
    assert header_dict['target'] == target
    assert header_dict['nonce'] == nonce
    assert header_dict['timestamp'] == timestamp
