# noinspection PySingleQuotedDocstring
'''
The Database Class. Using SQLite
'''
import sqlite3
from contextlib import closing
from os.path import join
from pathlib import Path

from .block import Block
from .formatter import Formatter
from .utxo import UTXO_OUTPUT


# noinspection PySingleQuotedDocstring
class DataBase:
    '''
    The DataBase object is instantiated with a directory path and file name for the db.

    The db has the following 2 tables:
        1) Raw Blocks
        2) UTXO Pool

    These tables have the following column structure:

    Raw Blocks: | raw_block |
    UTXO Pool: | tx_id | tx_index | amount | address | block_height |

    All variables are text variables (aka: strings). Where appropriate, inputs to functions are their respective
    integers. But as SQLite has max integers size of 2^63-1, all integers are stored in the db as hex strings.

    '''
    # Formatter
    f = Formatter()

    def __init__(self, dir_path: str, db_file: str):
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Get file_path for future use
        self.file_path = Path(dir_path, db_file).absolute().as_posix()

        # Verify db
        if self.get_tables() != ['raw_blocks', 'utxo_pool']:
            self.wipe_db()
            self.create_db()

    def wipe_db(self):
        table_list = self.get_tables()

        conn = sqlite3.connect(self.file_path)
        c = conn.cursor()

        for table_name in table_list:
            command = f"""DROP TABLE {table_name}"""
            c.execute(command)
            conn.commit()

        conn.close()

    def create_db(self):
        conn = sqlite3.connect(self.file_path)
        c = conn.cursor()

        # Table 1
        c.execute("""CREATE TABLE raw_blocks(
                    raw_block text
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

        conn.close()

    # --- GENERIC METHODS --- #

    def query_db(self, query: str, data=None):
        with closing(sqlite3.connect(self.file_path)) as con, con, closing(con.cursor()) as cur:
            query_executed = False
            while not query_executed:
                try:
                    if data:
                        cur.execute(query, data)
                    else:
                        cur.execute(query)
                    query_executed = True
                except sqlite3.OperationalError:
                    pass
            return cur.fetchall()

    def get_tables(self):
        table_list = []
        query = """SELECT name FROM sqlite_master WHERE type='table'"""
        list_of_tuples = self.query_db(query)
        if list_of_tuples:
            for table_tuple in list_of_tuples:
                (table_name,) = table_tuple
                table_list.append(table_name)
        return table_list

    # --- RAW BLOCKS --- #

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

    # POST METHODS
    def post_block(self, block: Block):
        # Raw Block table
        raw_block_query = """INSERT INTO raw_blocks VALUES (?)"""
        raw_block_data_tuple = (block.raw_block,)
        self.query_db(raw_block_query, raw_block_data_tuple)

    # DELETE METHODS
    def delete_block(self):
        # Only delete the last block
        height = self.get_height()['height']
        # Raw Block Table
        raw_block_query = """DELETE FROM raw_blocks where rowid = ?"""
        raw_block_data_tuple = (height + 1,)
        self.query_db(raw_block_query, raw_block_data_tuple)

    # --- UTXO POOL ---#

    # GET METHODS
    def get_utxo(self, tx_id: str, tx_index: int) -> dict:
        query = """SELECT * FROM utxo_pool WHERE tx_id = ? AND tx_index = ?"""
        utxo_list = self.query_db(query, (tx_id, hex(tx_index)))
        utxo_dict = {}
        if utxo_list:
            tx_id, h_index, h_amount, address, h_block_height = utxo_list[0]
            utxo_dict.update({
                "tx_id": tx_id,
                "tx_index": int(h_index, 16),
                "amount": int(h_amount, 16),
                "address": address,
                "block_height": int(h_block_height, 16)
            })
        return utxo_dict

    # Used in API for /<address>/ endpoint
    def get_utxos_by_address(self, address: str) -> dict:
        query = """SELECT tx_id, tx_index FROM utxo_pool WHERE address = ?"""
        list_of_utxo_tuples = self.query_db(query, (address,))
        utxo_dict = {'address': address, 'utxo_count': len(list_of_utxo_tuples)}

        # Get utxos as dicts
        for utxo_tuple in list_of_utxo_tuples:
            tx_id, h_index = utxo_tuple
            utxo_dict.update({
                f'utxo_{list_of_utxo_tuples.index(utxo_tuple)}': self.get_utxo(tx_id, int(h_index, 16))}
            )

        # Return dict
        return utxo_dict

    # Used in mine end of life algorithm
    def get_invested_amount(self, block_height: int):
        query = """SELECT amount, block_height from utxo_pool WHERE length(block_height) >= ?"""
        list_of_utxo_tuples = self.query_db(query, (len(hex(block_height)),))
        total_amount = 0
        for amount_tuple in list_of_utxo_tuples:
            (hex_amount, hex_block_height) = amount_tuple
            if int(hex_block_height, 16) >= block_height:
                total_amount += int(hex_amount, 16)
        return total_amount

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
