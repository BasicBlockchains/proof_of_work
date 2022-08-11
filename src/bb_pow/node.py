'''
The Node class
'''
import json
import socket
import threading
from collections import Counter
from multiprocessing import Process, Queue
from pathlib import Path
from basicblockchains_ecc.elliptic_curve import secp256k1
from src.bb_pow.blockchain import Blockchain
from src.bb_pow.miner import Miner
from src.bb_pow.wallet import Wallet
from src.bb_pow.block import Block
from src.bb_pow.decoder import Decoder
from src.bb_pow.formatter import Formatter
from src.bb_pow.transactions import Transaction, MiningTransaction
from src.bb_pow.timestamp import utc_to_seconds


class Node:
    # Directory defaults
    DIR_PATH = './data/'
    DB_FILE = 'chain.db'

    # Decoder and formatter
    d = Decoder()
    f = Formatter()

    # Timeout for running processes
    MINER_TIMEOUT = 1

    def __init__(self, dir_path=DIR_PATH, db_file=DB_FILE, seed=None):
        # Curve for cryptography
        self.curve = secp256k1()

        # Set path and filename variables
        self.dir_path = dir_path
        self.db_file = db_file

        # Create Blockchain object
        self.blockchain = Blockchain(self.dir_path, self.db_file)

        # Create Miner object
        self.miner = Miner()

        # Create Block queue for miner
        self.block_queue = Queue()

        # Create mining flag for monitoring
        self.is_mining = False

        # Create Wallet object
        self.wallet = Wallet(seed)

        # Create transaction lists
        self.validated_transactions = []
        self.orphaned_transactions = []
        self.block_transactions = []

        # Create utxo consumption list
        self.consumed_utxos = []

        # Create orphaned block list
        self.orphaned_blocks = []

    # --- PROPERTIES --- #
    @property
    def last_block(self):
        return self.blockchain.last_block

    @property
    def height(self):
        return self.blockchain.height

    @property
    def target(self):
        return self.blockchain.target

    @property
    def mining_reward(self):
        return self.blockchain.mining_reward

    @property
    def total_mining_amount(self):
        return self.blockchain.total_mining_amount

    # --- MINER --- #
    def start_miner(self):
        '''
        Turn on mining thread
        set is_mining to True
        Mining conducted from the monitor
        '''
        if not self.is_mining:
            # Logging
            self.is_mining = True
            self.mining_thread = threading.Thread(target=self.mining_monitor)
            self.mining_thread.start()
        else:
            # Logging
            print('Miner already running.')

    def mining_monitor(self):
        while self.is_mining:
            unmined_block = self.create_next_block()
            self.mining_process = Process(target=self.mine_block, args=(unmined_block,))
            self.mining_process.start()  # Mining happens in its own process

            # Handle blocking function
            next_block = None
            mining = True
            while mining:
                try:
                    next_block = self.block_queue.get(timeout=self.MINER_TIMEOUT)  # Next block is waiting in the thread
                    mining = False
                except Exception:
                    # If not mining, end monitor
                    if not self.is_mining:
                        mining = False
            if next_block:
                added = self.add_block(next_block)
                if not added:
                    self.is_mining = False

    def mine_block(self, unmined_block: Block):
        mined_block = self.miner.mine_block(unmined_block)
        self.block_queue.put(mined_block)

    def stop_miner(self):
        if self.is_mining:
            self.is_mining = False
            self.miner.stop_mining()

    def create_next_block(self):
        # Get as many validated transactions that will fit in the Block
        bit_size = 0
        self.block_transactions = []
        while bit_size <= self.f.MAXIMUM_BIT_SIZE and self.validated_transactions != []:
            self.block_transactions.append(self.validated_transactions.pop(0))  # Add first validated transaction
            bit_size += len(self.block_transactions[-1].raw_tx) * 4  # Increase bit_size by number of hex chars * 4

        # Get block fees
        block_fees = 0
        for tx in self.block_transactions:
            block_fees += self.get_fees(tx)

        # Create Mining Transaction
        mining_tx = MiningTransaction(self.height + 1, self.mining_reward, block_fees, self.wallet.address)

        # Return unmined block
        return Block(self.last_block.id, self.target, 0, utc_to_seconds(), mining_tx, self.block_transactions)

    def get_fees(self, tx: Transaction):
        '''
        We sum up all input amounts and subtract total output amount
        '''
        total_input_amount = 0
        total_output_amount = 0

        # Iterate over all inputs
        for utxo_input in tx.inputs:
            tx_id = utxo_input.tx_id
            tx_index = utxo_input.index
            utxo_exists = self.blockchain.chain_db.get_utxo(tx_id, tx_index)
            if utxo_exists:
                total_input_amount += utxo_exists['output']['amount']
            # If utxo has been consumed, look for it in the chain
            else:
                temp_tx = self.blockchain.get_tx_by_id(tx_id)
                if temp_tx:
                    total_input_amount += temp_tx.outputs[tx_index].amount
                else:
                    # Logging
                    print(f'Unable to find referenced utxo in chain or utxo pool. tx_id: {tx_id}, index: {tx_index}')

        # Iterate over all outputs
        for utxo_output in tx.outputs:
            total_output_amount += utxo_output.amount

        # Fees = total_input_amount - total_output_amount
        return max(0, total_input_amount - total_output_amount)

    # --- ADD BLOCK --- #
    def add_block(self, block: Block) -> bool:
        added = self.blockchain.add_block(block)
        return added
