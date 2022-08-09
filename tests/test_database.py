'''
Tests for the database class
'''
import secrets

from src.bb_pow.database import DataBase
from src.bb_pow.block import Block
import os
from pathlib import Path
from .test_block import get_random_transaction, get_random_utxo_input, get_random_utxo_output, get_random_mining_tx
from .test_wallet import random_tx_id
from src.bb_pow.wallet import Wallet
import json


# def test_utxo_methods():
#     # Create db with path in tests directory
#     current_path = os.getcwd()
#     if '/tests' in current_path:
#         dir_path = current_path + '/data/test_database/'
#     else:
#         dir_path = './tests/data/test_database/'
#     file_name = 'test_utxos.db'
#     db = DataBase(dir_path, file_name)
#
#     # Known address
#     w = Wallet()
#
#     # Get random utxos
#     random_length = 0
#     while random_length < 1:
#         random_length = secrets.randbits(4)
#     utxo_list = []
#     tx_list = []
#     for x in range(random_length):
#         utxo_list.append(get_random_utxo_output())
#         tx_list.append(random_tx_id())
#
#     for utxo in utxo_list:
#         utxo.address = w.address
#
#     # post_utxo
#     for x in range(len(utxo_list)):
#         db.post_utxo(tx_list[x], x, utxo_list[x])
#
#     # get_utxo
#     temp_list = []  # <-- used in get_utxos_by_address
#     for y in range(random_length):
#         utxo_dict = {
#             "tx_id": tx_list[y],
#             "tx_index": y,
#             "output": json.loads(utxo_list[y].to_json)
#         }
#         assert db.get_utxo(tx_list[y], y) == utxo_dict
#         temp_list.append(utxo_dict)
#
#     # get_utxos_by_address
#     address_dict = {
#         "address": w.address,
#         "utxo_count": random_length
#     }
#     for z in range(random_length):
#         address_dict.update({
#             f"utxo_{z}": temp_list[z]
#         })
#     assert address_dict == db.get_utxos_by_address(w.address)
#
#     # get_<...>_by_utxo
#     random_index = secrets.randbelow(random_length)
#     result_dict_a = db.get_address_by_utxo(tx_list[random_index], random_index)
#     result_dict_b = db.get_amount_by_utxo(tx_list[random_index], random_index)
#     result_dict_c = db.get_block_height_by_utxo(tx_list[random_index], random_index)
#     assert result_dict_a["address"] == w.address
#     assert result_dict_b["amount"] == utxo_list[random_index].amount
#     assert result_dict_c["block_height"] == utxo_list[random_index].block_height
#
#     # delete_utxo
#     for w in range(random_length):
#         db.delete_utxo(tx_list[w], w)
#         assert db.get_utxo(tx_list[w], w) == {}


def test_block_header_methods():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_database/'
    else:
        dir_path = './tests/data/test_database/'
    file_name = 'test_headers.db'
    db = DataBase(dir_path, file_name)

    # Random length
    random_length = 3

    # Post Blocks
    block_list = []
    for x in range(random_length):
        # Create random Block
        prev_id = random_tx_id()
        target = secrets.randbits(256)
        nonce = secrets.randbits(64)
        timestamp = secrets.randbits(64)

        tx_length = 0
        while tx_length < 1:
            tx_length = secrets.randbits(2)
        transactions = [get_random_transaction() for r in range(tx_length)]

        mining_tx = get_random_mining_tx()

        sample_block = Block(prev_id, target, nonce, timestamp, mining_tx, transactions)
        block_list.append(sample_block)

        # Post
        db.post_block(sample_block)

    # get_block_ids
    id_dict = {
        "chain_height": random_length
    }
    for y in range(random_length):
        id_dict.update({
            f"id_{y}": block_list[y].id
        })
    assert id_dict == db.get_block_ids()

    # get methods
    for z in range(random_length):
        temp_block = block_list[z]
        height_dict = {
            "id": temp_block.id,
            "prev_id": temp_block.prev_id,
            "merkle_root": temp_block.merkle_root,
            "target": temp_block.target,
            "nonce": temp_block.nonce,
            "timestamp": temp_block.timestamp
        }
        raw_block_dict = {
            "raw_block": temp_block.raw_block
        }
        assert db.get_headers_by_height(z) == height_dict
        assert db.get_headers_by_id(temp_block.id) == height_dict
        assert db.get_headers_by_merkle_root(temp_block.merkle_root) == height_dict
        assert db.get_raw_block(z) == raw_block_dict

    # Delete method
    for w in range(random_length):
        db.delete_block(w)
        assert db.get_headers_by_height(w) == {}
        assert db.get_raw_block(w) == {}
