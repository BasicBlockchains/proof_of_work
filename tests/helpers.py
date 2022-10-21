'''
Helper functions for tests
'''

import random
import secrets
import string
from hashlib import sha256
import logging

from basicblockchains_ecc.elliptic_curve import secp256k1
from .context import UTXO_INPUT, UTXO_OUTPUT, Transaction, MiningTransaction, utc_to_seconds, Header, Block, Node, \
    Blockchain, Wallet, mine_a_block, Formatter

# --- Constants --- #
curve = secp256k1()
f = Formatter()


# Random hash
def random_hash():
    random_string = ''
    for x in range(secrets.randbits(16)):
        random_string += random.choice(string.ascii_letters)
    return sha256(random_string.encode()).hexdigest()


# Random private_key
def random_private_key():
    return secrets.randbits(f.HASH_CHARS * 4)


# Random public key
def random_public_key():
    return curve.scalar_multiplication(random_private_key(), curve.generator)


# Random cpk
def random_cpk():
    return f.cpk(random_public_key())


# Random signature for a given tx_id
def random_signature(tx_id: str):
    return f.signature(random_private_key(), tx_id)


# Random index for utxo_input
def random_index():
    return secrets.randbelow(pow(16, f.INDEX_CHARS))


# Random amount
def random_amount():
    return secrets.randbelow(pow(16, f.AMOUNT_CHARS))


# Random nonce
def random_nonce():
    return secrets.randbelow(pow(16, f.NONCE_CHARS))


# Random reward
def random_reward():
    return secrets.randbelow(pow(16, f.REWARD_CHARS))


# Random block fees
def random_block_fees():
    return secrets.randbelow(pow(16, f.AMOUNT_CHARS))


# Random height
def random_height():
    return secrets.randbelow(pow(16, f.HEIGHT_CHARS))


# Address from private key
def address_from_private_key(private_key: int):
    return f.address(f.cpk(curve.scalar_multiplication(private_key, curve.generator)))


# Random address
def random_address():
    return address_from_private_key(secrets.randbits(256))


# Random utxo_input
def random_utxo_input():
    tx_id = random_hash()
    index = random_index()
    signature = random_signature(tx_id)
    return UTXO_INPUT(tx_id, index, signature)


# Random utxo output
def random_utxo_output():
    amount = random_amount()
    address = random_address()
    block_height = random_height()
    return UTXO_OUTPUT(amount, address, block_height)


# Random target coefficient
def random_target_coefficient():
    return secrets.randbits(f.TARGET_COEFF_CHARS * 4)


# Random target exponent
def random_target_exponent():
    exp = 0
    while exp < 3 or exp > 31:
        exp = secrets.randbits(f.TARGET_EXPONENT_CHARS * 4)
    return exp


# Random target
def random_target():
    return f.target_from_parts(random_target_coefficient(), random_target_exponent())


# Random Mining Transaction
def random_mining_tx():
    height = random_height()
    reward = random_reward()
    block_fees = random_block_fees()
    address = random_address()
    block_height = random_height()

    while reward + block_fees > pow(16, f.REWARD_CHARS):
        block_fees = int(block_fees // 2)
        reward = int(reward // 2)

    return MiningTransaction(height, reward, block_fees, address, block_height)


# Random Transaction
def random_tx():
    input_count = secrets.randbits(4)
    output_count = secrets.randbits(4)

    inputs = []
    for x in range(input_count):
        inputs.append(random_utxo_input())

    outputs = []
    for y in range(output_count):
        outputs.append(random_utxo_output())

    return Transaction(inputs=inputs, outputs=outputs)


# Random Block Header
def random_header():
    prev_id = random_hash()
    merkle_root = random_hash()
    target = random_target()
    nonce = random_nonce()
    timestamp = utc_to_seconds()

    return Header(prev_id, merkle_root, target, nonce, timestamp)


# Random Block Header with merkle_root input
def random_header_with_merkle_root(merkle_root: str):
    prev_id = random_hash()
    target = random_target()
    nonce = random_nonce()
    timestamp = utc_to_seconds()

    return Header(prev_id, merkle_root, target, nonce, timestamp)


# Random unmined block
def random_unmined_block(prev_id: id, height: int, reward: int, target: int):
    address = random_address()
    nonce = random_nonce()
    mining_tx = MiningTransaction(height, reward, 0, address, height + f.MINING_DELAY)
    return Block(prev_id, target, nonce, utc_to_seconds(), mining_tx, [])


def random_unmined_block_with_address(prev_id: id, height: int, reward: int, target: int, address: str):
    nonce = random_nonce()
    mining_tx = MiningTransaction(height, reward, 0, address, height + f.MINING_DELAY)
    return Block(prev_id, target, nonce, utc_to_seconds(), mining_tx, [])


# Genesis blocks
def create_node_gb(node: Node):
    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('CRITICAL')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    gt = MiningTransaction(0, f.HALVING_NUMBER * f.BASIC_TO_BBS, 0,
                           Wallet(seed=0, save=False, logger=test_logger).address, 0xffffffffffffffff)
    ugb = Block('', f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20), 0, utc_to_seconds(), gt, [])
    gb = mine_a_block(ugb)
    node.blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20)
    node.blockchain.f.MINING_DELAY = 0
    node.blockchain.GENESIS_NONCE = gb.nonce
    node.blockchain.GENESIS_TIMESTAMP = gb.timestamp
    node.blockchain.chain_db.wipe_db()
    node.blockchain.chain_db.create_db()
    node.blockchain.chain = []
    node.blockchain.height = -1
    node.blockchain.add_block(gb)
    return node


def copy_node_gb(node: Node, gb: Block):
    node.blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20)
    node.blockchain.f.MINING_DELAY = 0
    node.blockchain.GENESIS_NONCE = gb.nonce
    node.blockchain.GENESIS_TIMESTAMP = gb.timestamp
    node.blockchain.chain_db.wipe_db()
    node.blockchain.chain_db.create_db()
    node.blockchain.chain = []
    node.blockchain.height = -1
    node.blockchain.add_block(gb)
    return node


def create_blockchain_gb(blockchain: Blockchain):
    # Create test logger
    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('CRITICAL')
    test_logger.propagate = False
    sh = logging.StreamHandler()
    sh.formatter = logging.Formatter(f.LOGGING_FORMAT)
    test_logger.addHandler(sh)

    gt = MiningTransaction(0, f.HALVING_NUMBER * f.BASIC_TO_BBS, 0,
                           Wallet(seed=0, save=False, logger=test_logger).address, 0xffffffffffffffff)
    ugb = Block('', f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20), 0, utc_to_seconds(), gt, [])
    gb = mine_a_block(ugb)
    blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x20)
    blockchain.f.MINING_DELAY = 0
    blockchain.GENESIS_NONCE = gb.nonce
    blockchain.GENESIS_TIMESTAMP = gb.timestamp
    blockchain.chain_db.wipe_db()
    blockchain.chain_db.create_db()
    blockchain.chain = []
    blockchain.height = -1
    blockchain.add_block(gb)
    return blockchain
