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

        # # Start REST API
        # self.app.run()

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
                # Logging
                print(f'Block mined by node. Height: {self.height}, Added: {added}')

    def mine_block(self, unmined_block: Block):
        mined_block = self.miner.mine_block(unmined_block)
        self.block_queue.put(mined_block)

    def stop_miner(self):
        if self.is_mining:
            if self.mining_process.is_alive():
                self.mining_process.terminate()
            self.is_mining = False
            while self.mining_thread.is_alive():
                pass

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
        if added:
            # Remove validated transactions
            validated_tx_index = self.validated_transactions.copy()
            for tx in validated_tx_index:
                if tx.id in self.last_block.tx_ids:
                    self.validated_transactions.remove(tx)
                    # Remove consumed utxos
                    for input in tx.inputs:
                        input_tuple = (input.tx_id, input.index)
                        if input_tuple in self.consumed_utxos:
                            self.consumed_utxos.remove(input_tuple)

            # Check if orphaned transactions are now valid
            self.check_for_tx_parents()

            # Check if orphaned blocks are now valid
            self.check_for_block_parents()
        return added

    # --- ADD TRANSACTION --- #

    def add_transaction(self, transaction: Transaction) -> bool:
        # Make sure tx is not in chain
        existing_tx = self.blockchain.get_tx_by_id(transaction.id)
        if existing_tx:
            # Logging
            print('Transaction already in chain.')
            return False

        # Iterate over validated transactions to make sure transaction not there
        for vt in self.validated_transactions:
            if vt.raw_tx == transaction.raw_tx:
                # Logging
                print('Transaction already in validated tx pools.')
                return False

        # Make sure orphaned transaction was removed from orphaned_transactions list
        for ot in self.orphaned_transactions:
            if ot.raw_tx == transaction.raw_tx:
                # Logging
                print('Transaction already in orphaned tx pools.')
                return False

        # Set orphaned transaction Flag
        orphan = False

        # Validate inputs
        total_input_amount = 0
        for i in transaction.inputs:  # Looping over utxo_input objects

            # Get the row index for the output utxo
            tx_id = i.tx_id
            tx_index = i.index

            # Get values from db
            amount_dict = self.blockchain.chain_db.get_amount_by_utxo(tx_id, tx_index)
            address_dict = self.blockchain.chain_db.get_address_by_utxo(tx_id, tx_index)
            block_height_dict = self.blockchain.chain_db.get_block_height_by_utxo(tx_id, tx_index)

            # If values are empty lists mark for orphan
            if amount_dict == {} or address_dict == {} or block_height_dict == {}:
                # Logging
                print(f'Unable to find utxo with id {tx_id} and index {tx_index}')
                orphan = True


            # Validate the referenced output utxo
            else:
                # Get values
                amount = amount_dict['amount']
                address = address_dict['address']
                block_height = block_height_dict['block_height']

                # Validate the block_height
                if block_height > self.height:
                    # Logging
                    print(f'Block height error. UTXO not available until block {block_height}')
                    return False

                # Validate the address from compressed public key
                cpk, (r, s) = self.d.decode_signature(i.signature)
                if not self.f.address(cpk) == address:
                    # Logging
                    print(f'CPK/Address error. Address: {address}, CPK Address: {self.f.address(cpk)}')
                    return False

                # Validate the signature
                if not self.d.verify_signature(i.signature, tx_id):
                    # Logging
                    print('Signature error')
                    return False

                # Check input not already scheduled for consumption
                input_tuple = (tx_id, tx_index)
                if input_tuple not in self.consumed_utxos:
                    self.consumed_utxos.append(input_tuple)
                else:
                    # Logging
                    print('Utxo already consumed by this node')
                    return False

                # Increase total_input_amount
                total_input_amount += amount

        # If not flagged for orphaned
        if not orphan:
            # Get the total output amount
            total_output_amount = 0
            for t in transaction.outputs:
                total_output_amount += t.amount

            # Verify the total output amount
            if total_output_amount > total_input_amount:
                # Logging
                print('Input/Output amount error in tx')
                # Unconsume the input tuple in consumed
                for i in transaction.inputs:
                    tx_tuple = (i.tx_id, i.output_index)
                    if tx_tuple in self.consumed_utxos:
                        self.consumed_utxos.remove(tx_tuple)
                return False

            # Add tx to validated tx pool
            self.validated_transactions.append(transaction)

        # Flagged for orphaned. Add to orphan pool
        else:
            self.orphaned_transactions.append(transaction)

        return True

    # --- ORPHANS --- #

    def check_for_tx_parents(self):
        '''
        After a Block is saved, we iterate over all orphaned transactions to see if their parent UTXOs were saved.
        However, when validating a transaction, we check if it's raw_tx is already in the validated_transactions and
        orphaned_transactions pool. Hence, for the Node, when checking for an orphans parents, we make sure the
        transaction itself is removed from the orphaned_transaction pool.
        '''
        orphan_index = self.orphaned_transactions.copy()
        for x in range(0, len(orphan_index)):
            tx = self.orphaned_transactions.pop(0)
            self.add_transaction(tx)

    def check_for_block_parents(self):
        orphan_index = self.orphaned_blocks.copy()
        for x in range(0, len(orphan_index)):
            block = self.orphaned_blocks.pop(0)
            self.add_block(block)
