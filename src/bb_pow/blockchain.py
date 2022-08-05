'''
The Blockchain Class
'''

from .block import Block
from .database import DataBase
from pathlib import Path


class Blockchain():
    '''
    The Blockchain will be saving data to a db, and so can be instantiated with a directory path other than default.
    Similarly, the filenames for the db can be other than default "chain.db".
    '''
    DIR_PATH = './data/'
    DB_FILE = 'chain.db'

    # --CONSTANTS
    TOTAL_MINING_AMOUNT = pow(2, 64) - 1
    REWARD = pow(10, 9)
    TARGET = 0x0
    HEARTBEAT = 60

    def __init__(self, dir_path=DIR_PATH, db_file=DB_FILE):
        # Set path and filename variables
        self.dir_path = dir_path
        self.db_file = db_file

        # Create db - Database will create file
        self.chain_db = DataBase(self.dir_path, self.db_file)

        # Create chain list to hold last HEARTBEAT blocks
        self.chain = []

        # Create genesis block
        self.create_genesis_block()

    def add_block(self, block: Block):
        # Validate Block
        # Consume UTXOS in tx inputs
        # Add UTXOS in tx outputs
        # Add block to mem_chain
        # Save block_headers to db
        # Save raw_block to db
        # Adjust total_mining_amount
        # Adjust target if HEARTBEAT blocks have passed
        # Adjust reward if total_mining_amount reaches a certain level
        pass

    def create_genesis_block(self):
        pass
