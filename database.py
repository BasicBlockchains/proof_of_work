'''
The Database Class. Using SQLite
'''
import json
import sqlite3
from contextlib import closing
from os.path import join
from pathlib import Path

from block import Block
from formatter import Formatter
from utxo import UTXO_OUTPUT


class DataBase:
    '''
    The db can be instantiated with a directory path and filename. Any existing db will be DELETED.

    The db will be created with 3 tables:
        1) Block headers
        2) UTXO Pool
        3) Raw blocks



    NOTE: SQLite has a max integer size of 2^63-1 so we store integers as hex strings

    '''
    # Formatter
    f = Formatter()

    def __init__(self, dir_path: str, db_file: str):
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Get file_path for future use
        self.file_path = join(dir_path, db_file)

        # if Path(self.file_path).exists():
        #     self.wipe_db()
        # self.create_db()

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

    def get_height(self):
        query = """SELECT COUNT(*) FROM raw_blocks"""
        height_tuple = self.query_db(query)
        (height,) = height_tuple[0]
        height_dict = {
            "height": height - 1
        }
        return height_dict

    def get_raw_block(self, height: int):
        query = """SELECT raw_block from raw_blocks where rowid = ?"""
        data_tuple = (height + 1,)
        raw_block_tuple_list = self.query_db(query, data_tuple)
        raw_block_dict = {}
        if raw_block_tuple_list:
            (raw_block,) = raw_block_tuple_list[0]
            raw_block_dict.update({
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
        query = """SELECT * FROM block_headers WHERE rowid = ?"""
        header_tuple_list = self.query_db(query, (height + 1,))
        header_dict = {}
        if header_tuple_list:
            id, prev_id, merkle_root, target, h_nonce, h_timestamp = header_tuple_list[0]
            header_dict.update({
                "id": id,
                "prev_id": prev_id,
                "merkle_root": merkle_root,
                "target": self.f.target_from_int(int(target, 16)),
                "nonce": int(h_nonce, 16),
                "timestamp": int(h_timestamp, 16)
            })

        return header_dict

    def get_headers_by_id(self, id: str):
        query = """SELECT * FROM block_headers WHERE id = ?"""
        header_tuple_list = self.query_db(query, (id,))
        header_dict = {}
        if header_tuple_list:
            _, prev_id, merkle_root, target, h_nonce, h_timestamp = header_tuple_list[0]
            header_dict.update({
                "id": id,
                "prev_id": prev_id,
                "merkle_root": merkle_root,
                "target": self.f.target_from_int(int(target, 16)),
                "nonce": int(h_nonce, 16),
                "timestamp": int(h_timestamp, 16)
            })

        return header_dict

    def get_headers_by_merkle_root(self, merkle_root: str):
        query = """SELECT * FROM block_headers WHERE merkle_root = ?"""
        header_tuple_list = self.query_db(query, (merkle_root,))
        header_dict = {}
        if header_tuple_list:
            id, prev_id, _, target, h_nonce, h_timestamp = header_tuple_list[0]
            header_dict.update({
                "id": id,
                "prev_id": prev_id,
                "merkle_root": merkle_root,
                "target": self.f.target_from_int(int(target, 16)),
                "nonce": int(h_nonce, 16),
                "timestamp": int(h_timestamp, 16)
            })

        return header_dict

    # POST METHODS
    def post_block(self, block: Block):
        # Header Table
        query = """INSERT INTO block_headers VALUES (?,?,?,?,?,?)"""
        data_tuple = (block.id, block.prev_id, block.merkle_root,
                      hex(block.target), hex(block.nonce), hex(block.timestamp))
        self.query_db(query, data_tuple)

        # Raw Block table
        raw_block_query = """INSERT INTO raw_blocks VALUES (?)"""
        raw_block_data_tuple = (block.raw_block,)
        self.query_db(raw_block_query, raw_block_data_tuple)

    # DELETE METHODS
    def delete_block(self, height: int):
        # Header Table
        query = """DELETE FROM block_headers WHERE rowid = ?"""
        data_tuple = (height + 1,)
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

    def get_utxos_by_tx_id(self, tx_id: str):
        query = """SELECT * from utxo_pool WHERE tx_id = ?"""
        list_of_utxo_tuples = self.query_db(query, (tx_id,))
        print(list_of_utxo_tuples)

        utxo_dict = {'tx_id': tx_id, 'utxo_count': len(list_of_utxo_tuples)}

        # Get utxos as dicts
        for tuple in list_of_utxo_tuples:
            tx_id, h_index, h_amount, address, h_block_height = tuple
            temp_utxo = UTXO_OUTPUT(int(h_amount, 16), address, int(h_block_height, 16))
            transaction_dict = {
                "tx_id": tx_id,
                "tx_index": int(h_index, 16),
                "output": json.loads(temp_utxo.to_json)
            }
            utxo_dict.update({f'utxo_{list_of_utxo_tuples.index(tuple)}': transaction_dict})

        # Return dict - json serializable
        return utxo_dict

    def get_total_amount_greater_than_block_height(self, block_height: int):
        query = """SELECT amount, block_height from utxo_pool WHERE length(block_height) >= ?"""
        list_of_utxo_tuples = self.query_db(query, (len(hex(block_height)),))
        # TESTING
        print(f'GET TOTAL AMOUNT CALL. LIST OF TUPLES: {list_of_utxo_tuples}')
        total_amount = 0
        for amount_tuple in list_of_utxo_tuples:
            (hex_amount, hex_block_height) = amount_tuple
            if int(hex_block_height, 16) >= block_height:
                total_amount += int(hex_amount, 16)
        return total_amount

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
