'''
The Database Class. Using SQLite
'''
import sqlite3
from .block import Block
from pathlib import Path
from os.path import join
from .utxo import UTXO_OUTPUT
from contextlib import closing
import json


class DataBase:
    '''
    The db can be instantiated with a directory path and filename. Any existing db will be DELETED.

    The db will be created with 3 tables:
        1) Block headers
        2) UTXO Pool
        3) Raw Block

    NOTE: SQLite has a max integer size of 2^63-1 so we store integers as hex strings

    '''

    def __init__(self, dir_path: str, db_file: str):
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Get file_path for future use
        self.file_path = join(dir_path, db_file)

        if Path(self.file_path).exists():
            self.wipe_db()
        self.create_db()

    def wipe_db(self):
        conn = sqlite3.connect(self.file_path)
        c = conn.cursor()

        # Remove Table 1
        c.execute("""DROP TABLE block_headers""")
        conn.commit()

        # Remove Table 2
        c.execute("""DROP TABLE utxo_pool""")
        conn.commit()

        # Remove Table 3
        c.execute("""DROP TABLE raw_blocks""")
        conn.commit()

        conn.close()

    def create_db(self):
        conn = sqlite3.connect(self.file_path)
        c = conn.cursor()

        # Table 1
        c.execute("""CREATE TABLE block_headers (
                    height text,
                    id text,                      
                    previous_id text, 
                    merkle_root text, 
                    target text, 
                    nonce text, 
                    timestamp text
                    )""")
        conn.commit()

        # Table 2
        c.execute("""CREATE TABLE utxo_pool (
                    tx_id text,
                    tx_index text,
                    amount text,
                    address text,
                    block_height text
                    )""")
        conn.commit()

        # Table 3
        c.execute("""CREATE TABLE raw_blocks(
                    raw_block text
                    )""")
        conn.commit()

        conn.close()

    ### --- GENERIC METHODS --- ###

    def query_db(self, query: str, data=None):
        with closing(sqlite3.connect(self.file_path)) as con, con, closing(con.cursor()) as cur:
            if data:
                cur.execute(query, data)
            else:
                cur.execute(query)
            return cur.fetchall()

    # GET METHODS

    def get_raw_block(self, height: int):
        query = """SELECT raw_block from raw_blocks where rowid = ?"""
        data_tuple = (height + 1,)
        raw_block_tuple_list = self.query_db(query, data_tuple)
        raw_block_dict = {}
        if raw_block_tuple_list:
            (raw_block,) = raw_block_tuple_list[0]
            raw_block_dict.update({
                "height": height,
                "raw_block": raw_block
            })
        return raw_block_dict

    def get_block_ids(self):
        query = """SELECT id from block_headers"""
        id_tuple_list = self.query_db(query)
        id_dict = {"chain_height": len(id_tuple_list)}
        for x in range(len(id_tuple_list)):
            (id,) = id_tuple_list[x]
            id_dict.update({
                f'id_{x}': id
            })
        return id_dict

    def get_headers_by_height(self, height: int) -> dict:
        query = """SELECT * FROM block_headers WHERE height = ?"""
        header_tuple_list = self.query_db(query, (hex(height),))
        header_dict = {}
        if header_tuple_list:
            _, id, prev_id, merkle_root, target, h_nonce, h_timestamp = header_tuple_list[0]
            header_dict.update({
                "height": height,
                "id": id,
                "prev_id": prev_id,
                "merkle_root": merkle_root,
                "target": int(target, 16),
                "nonce": int(h_nonce, 16),
                "timestamp": int(h_timestamp, 16)
            })

        return header_dict

    def get_headers_by_id(self, id: str):
        query = """SELECT * FROM block_headers WHERE id = ?"""
        header_tuple_list = self.query_db(query, (id,))
        header_dict = {}
        if header_tuple_list:
            h_height, _, prev_id, merkle_root, target, h_nonce, h_timestamp = header_tuple_list[0]
            header_dict.update({
                "height": int(h_height, 16),
                "id": id,
                "prev_id": prev_id,
                "merkle_root": merkle_root,
                "target": int(target, 16),
                "nonce": int(h_nonce, 16),
                "timestamp": int(h_timestamp, 16)
            })

        return header_dict

    def get_headers_by_merkle_root(self, merkle_root: str):
        query = """SELECT * FROM block_headers WHERE merkle_root = ?"""
        header_tuple_list = self.query_db(query, (merkle_root,))
        header_dict = {}
        if header_tuple_list:
            h_height, id, prev_id, _, target, h_nonce, h_timestamp = header_tuple_list[0]
            header_dict.update({
                "height": int(h_height, 16),
                "id": id,
                "prev_id": prev_id,
                "merkle_root": merkle_root,
                "target": int(target, 16),
                "nonce": int(h_nonce, 16),
                "timestamp": int(h_timestamp, 16)
            })

        return header_dict

    # POST METHODS
    def post_block(self, block: Block, height: int):
        # Header Table
        query = """INSERT INTO block_headers VALUES (?,?,?,?,?,?,?)"""
        data_tuple = (
            hex(height), block.id, block.previous_id, block.merkle_root, hex(block.target), hex(block.nonce),
            hex(block.timestamp))
        self.query_db(query, data_tuple)

        # Raw Block table
        raw_block_query = """INSERT INTO raw_blocks VALUES (?)"""
        raw_block_data_tuple = (block.raw_block,)
        self.query_db(raw_block_query, raw_block_data_tuple)

    # DELETE METHODS
    def delete_block(self, height: int):
        # Header Table
        query = """DELETE FROM block_headers WHERE height = ?"""
        data_tuple = (hex(height),)
        self.query_db(query, data_tuple)

        # Raw Block Table
        raw_block_query = """DELETE FROM raw_blocks where rowid = ?"""
        raw_block_data_tuple = (height + 1,)
        self.query_db(raw_block_query, raw_block_data_tuple)

    ###---UTXO POOL---###

    # GET METHODS

    def get_utxos_by_address(self, address: str) -> dict:
        query = """SELECT tx_id, tx_index,amount,block_height FROM utxo_pool WHERE address = ?"""
        list_of_utxo_tuples = self.query_db(query, (address,))
        utxo_dict = {'address': address, 'utxo_count': len(list_of_utxo_tuples)}

        # Get utxos as dicts
        for tuple in list_of_utxo_tuples:
            tx_id, h_index, h_amount, h_block_height = tuple
            temp_utxo = UTXO_OUTPUT(int(h_amount, 16), address, int(h_block_height, 16))
            transaction_dict = {
                "tx_id": tx_id,
                "tx_index": int(h_index, 16),
                "output": json.loads(temp_utxo.to_json)
            }
            utxo_dict.update({f'utxo_{list_of_utxo_tuples.index(tuple)}': transaction_dict})

        # Return dict - json serializable
        return utxo_dict

    def get_utxo(self, tx_id: str, tx_index: int) -> dict:
        query = """SELECT * FROM utxo_pool WHERE tx_id = ? AND tx_index = ?"""
        utxo_list = self.query_db(query, (tx_id, hex(tx_index)))
        utxo_dict = {}
        if utxo_list:
            tx_id, h_index, h_amount, address, h_block_height = utxo_list[0]
            temp_utxo = UTXO_OUTPUT(int(h_amount, 16), address, int(h_block_height, 16))
            utxo_dict.update({
                "tx_id": tx_id,
                "tx_index": int(h_index, 16),
                "output": json.loads(temp_utxo.to_json)
            })
        return utxo_dict

    def get_address_by_utxo(self, tx_id: str, tx_index: int):
        query = """SELECT address FROM utxo_pool WHERE tx_id = ? AND tx_index = ?"""
        result_list = self.query_db(query, (tx_id, hex(tx_index)))
        result_dict = {}
        if result_list:
            (address,) = result_list[0]
            result_dict.update({
                "address": address
            })
        return result_dict

    def get_amount_by_utxo(self, tx_id: str, tx_index: int):
        query = """SELECT amount FROM utxo_pool WHERE tx_id = ? AND tx_index = ?"""
        result_list = self.query_db(query, (tx_id, hex(tx_index)))
        result_dict = {}
        if result_list:
            (amount,) = result_list[0]
            result_dict.update({
                "amount": int(amount, 16)
            })
        return result_dict

    def get_block_height_by_utxo(self, tx_id: str, tx_index: int):
        query = """SELECT block_height FROM utxo_pool WHERE tx_id = ? AND tx_index = ?"""
        result_list = self.query_db(query, (tx_id, hex(tx_index)))
        result_dict = {}
        if result_list:
            (block_height,) = result_list[0]
            result_dict.update({
                "block_height": int(block_height, 16)
            })
        return result_dict

    # POST METHODS
    def post_utxo(self, tx_id: str, tx_index: int, utxo_output: UTXO_OUTPUT):
        query = """INSERT INTO utxo_pool VALUES (?,?,?,?,?)"""
        data_tuple = (tx_id, hex(tx_index), hex(utxo_output.amount), utxo_output.address, hex(utxo_output.block_height))
        self.query_db(query, data_tuple)

    # DELETE METHODS
    def delete_utxo(self, tx_id: str, tx_index: int):
        query = """DELETE FROM utxo_pool WHERE tx_id = ? AND tx_index = ?"""
        data_tuple = (tx_id, hex(tx_index))
        self.query_db(query, data_tuple)

    ### --- RAW BLOCKS --- ###
    # GET

    # POST
    def post_raw_block(self, raw_block: str):
        query = """INSERT INTO raw_blocks VALUES (?)"""
        data_tuple = (raw_block,)
        self.query_db(query, data_tuple)

    # DELETE
    def delete_raw_block(self, height: str):
        query = """DELETE FROM raw_blocks WHERE rowid = ?"""
        data_tuple = (height,)
        self.query_db(query, data_tuple)
