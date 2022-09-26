'''
Tests for the database class
'''
import json
import os
import secrets
from pathlib import Path

from .context import DataBase, Block, Formatter, utc_to_seconds
from .helpers import random_hash, random_utxo_output, random_address, random_tx, random_mining_tx, \
    random_target, random_nonce


def test_utxo_methods():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_database/'
    else:
        dir_path = './tests/data/test_database/'
    file_name = 'test_utxos.db'

    # Start with empty db
    db = DataBase(dir_path, file_name)
    db.wipe_db()
    db.create_db()

    # Known address
    fixed_address = random_address()

    # Get random utxos
    random_length = 0
    while random_length < 1:
        random_length = secrets.randbits(4)
    utxo_list = []
    tx_list = []
    for x in range(random_length):
        utxo_list.append(random_utxo_output())
        tx_list.append(random_hash())

    for utxo in utxo_list:
        utxo.address = fixed_address

    # post_utxo
    for x in range(len(utxo_list)):
        db.post_utxo(tx_list[x], x, utxo_list[x])

    # get_utxo
    temp_list = []  # <-- used in get_utxos_by_address
    for y in range(random_length):
        utxo_dict = {
            "tx_id": tx_list[y],
            "tx_index": y,
            "amount": utxo_list[y].amount,
            "address": utxo_list[y].address,
            "block_height": utxo_list[y].block_height
        }
        assert db.get_utxo(tx_list[y], y) == utxo_dict
        temp_list.append(utxo_dict)

    # get_utxos_by_address
    address_dict = {
        "address": fixed_address,
        "utxo_count": random_length
    }
    for z in range(random_length):
        address_dict.update({
            f"utxo_{z}": temp_list[z]
        })
    assert address_dict == db.get_utxos_by_address(fixed_address)

    # delete_utxo
    for w in range(random_length):
        db.delete_utxo(tx_list[w], w)
        assert db.get_utxo(tx_list[w], w) == {}


def test_block_methods():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_database/'
    else:
        dir_path = './tests/data/test_database/'
    file_name = 'test_headers.db'

    # Start with empty db
    db = DataBase(dir_path, file_name)
    db.wipe_db()
    db.create_db()

    # Formatter
    f = Formatter()

    # Random length
    random_length = 0
    while random_length < 1:
        random_length = secrets.randbits(4)

    # Post Blocks
    block_list = []
    # Create random Blocks
    for x in range(random_length):
        # Random block vals
        prev_id = random_hash()
        target = random_target()
        nonce = random_nonce()
        timestamp = utc_to_seconds()

        # Tx count
        tx_count = 0
        while tx_count < 1:
            tx_count = secrets.randbits(4)

        # Random tx list
        transactions = [random_tx() for _ in range(tx_count)]

        # Random mining tx
        mining_tx = random_mining_tx()

        sample_block = Block(prev_id, target, nonce, timestamp, mining_tx, transactions)
        block_list.append(sample_block)

        # Post
        db.post_block(sample_block)

    # get methods
    for z in range(random_length):
        temp_block = block_list[z]
        raw_block_dict = {
            "raw_block": temp_block.raw_block
        }

        assert db.get_raw_block(z) == raw_block_dict

    # Delete method
    for w in range(random_length):
        db.delete_block()
        assert db.get_raw_block(random_length - w) == {}
