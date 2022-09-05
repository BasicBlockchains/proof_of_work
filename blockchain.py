'''
The Blockchain Class

TODO: During loading, account for file existing which doesn't contain correct genesis block
'''

from pathlib import Path
import logging
from basicblockchains_ecc.elliptic_curve import secp256k1

from block import Block
from database import DataBase
from decoder import Decoder
from formatter import Formatter
from transactions import MiningTransaction
from utxo import UTXO_OUTPUT
from wallet import Wallet


class Blockchain():
    '''
    The Blockchain will be saving data to a db, and so can be instantiated with a directory path other than default.
    Similarly, the filenames for the db can be other than default "chain.db".
    '''
    # Genesis values
    GENESIS_NONCE = 731041  # Tuned to production values in Formatter
    GENESIS_TIMESTAMP = 1664631000  # October 1st, 9:30 AM EST // 1:30 PM UTC

    # Directory defaults
    DIR_PATH = 'src/data/'
    DB_FILE = 'chain.db'

    # Decoder and formatter
    d = Decoder()
    f = Formatter()

    def __init__(self, dir_path=DIR_PATH, db_file=DB_FILE, logger=None):
        # Curve for cryptography
        self.curve = secp256k1()

        # Set path and filename variables
        self.dir_path = dir_path
        self.db_file = db_file

        # Check for db
        new_db = False if Path(self.dir_path, self.db_file).exists() else True

        # Create db - Database will create file
        self.chain_db = DataBase(self.dir_path, self.db_file)
        if new_db:  # Create db if path doesn't already exist
            self.chain_db.create_db()

        # Mining values
        self.total_mining_amount = self.f.TOTAL_MINING_AMOUNT
        self.mining_reward = 0
        self.target = self.f.target_from_parts(self.f.STARTING_TARGET_COEFFICIENT, self.f.STARTING_TARGET_EXPONENT)
        self.heartbeat = self.f.HEARTBEAT

        # Create chain list to hold last HEARTBEAT blocks
        self.chain = []

        # Create fork list to index forked blocks
        self.forks = []

        # Create load_count variable for loading chain
        self.load_count = -1

        # Create genesis block - if db is new, then loading = False
        self.add_block(self.create_genesis_block(), loading=not new_db)

        # Load chain if it exists
        self.load_chain()

    # Properties
    @property
    def height(self):
        return self.chain_db.get_height()['height']

    @property
    def last_block(self):
        return self.chain[-1]

    # Block methods
    def validate_block(self, block: Block) -> bool:
        # Check previous id
        if block.prev_id != self.last_block.id:
            # Logging
            print('Block failed validation. Block.prev_id != last_block.id')
            return False

        # Check target
        if int(block.id, 16) > self.target:
            # Logging
            print('Block failed validation. Block id bigger than target')
            return False

        # Check Mining Tx height
        if block.mining_tx.height != self.last_block.mining_tx.height + 1:
            # Logging
            print('Block failed validation. Mining_tx height incorrect')
            return False

        # Check Mining UTXO block_height
        if block.mining_tx.mining_utxo.block_height < self.last_block.mining_tx.height + 1 + self.f.MINING_DELAY:
            # Logging
            print('Block failed validation. Mining tx block height incorrect')
            # print(f'Block height in block: {block.mining_tx.mining_utxo.block_height}')
            # print(f'Last block mining tx height + 1: {self.last_block.mining_tx.height + 1}')
            # print(f'Mining delay: {self.f.MINING_DELAY}')
            return False

        # Check fees + reward = amount in mining_utxo
        block_total = block.mining_tx.block_fees + block.mining_tx.reward
        if block_total != block.mining_tx.mining_utxo.amount:
            # Logging
            print('Block failed validation. Block total incorrect')
            return False

        # TODO: Enable in production
        # # Make sure timestamp is increasing
        # if block.timestamp <= self.last_block.timestamp:
        #     # Logging
        #     print('Block failed validation. Block time too early.')
        #     return False

        # Check each tx
        fees = 0
        for tx in block.transactions:
            input_amount = 0
            output_amount = 0
            for input_utxo in tx.inputs:
                # Get UTXO_INPUT values
                tx_id = input_utxo.tx_id
                index = input_utxo.index
                signature = input_utxo.signature
                cpk, ecdsa_tuple = self.d.decode_signature(signature)

                # Check utxo_exists
                utxo_dict = self.chain_db.get_utxo(tx_id, index)
                if not utxo_dict:
                    # Logging
                    return False

                # Verify address
                utxo_address = utxo_dict['output']['address']
                temp_address = self.f.address(cpk)
                if temp_address != utxo_address:
                    # Logging
                    return False

                # Verify signature
                if not self.curve.verify_signature(ecdsa_tuple, tx_id, self.curve.decompress_point(cpk)):
                    # Logging
                    return False

                # Update amount
                input_amount += self.chain_db.get_amount_by_utxo(tx_id, index)['amount']

            for output_utxo in tx.outputs:
                output_amount += output_utxo.amount

            # Check input_amount < output_amount
            if input_amount < output_amount:
                # Logging
                return False

            fees += input_amount - output_amount

        # Verify fees in block_transactions agrees with MiningTx
        if fees != block.mining_tx.block_fees:
            # Logging
            print('Block failed validation. Block fees incorrect')
            # print(f'Fees: {fees}')
            # print(f'Block mining tx fees: {block.mining_tx.block_fees}')
            return False

        return True

    def add_block(self, block: Block, loading=False) -> bool:

        # Account for genesis
        if self.chain == []:
            valid_block = True
        # Account for loading from file
        elif loading:
            valid_block = True
        # Account for same block being gossiped back
        elif block.id == self.last_block.id:
            return False
        # Account for fork block
        elif max(1, self.height - self.f.HEARTBEAT) <= block.height <= self.height:
            self.create_fork(block)
            return False
        else:
            # Validate Block
            valid_block = self.validate_block(block)

        if valid_block:
            if not loading:
                # Consume UTXOS
                for tx in block.transactions:
                    # Consume UTXOS in tx inputs
                    for utxo_input in tx.inputs:
                        self.chain_db.delete_utxo(utxo_input.tx_id, utxo_input.index)

                    # Add UTXOS in tx outputs
                    for utxo_output in tx.outputs:
                        self.chain_db.post_utxo(tx.id, tx.outputs.index(utxo_output), utxo_output)

                # Add UTXOs in Mining Tx
                self.chain_db.post_utxo(block.mining_tx.id, 0, block.mining_tx.mining_utxo)

                # Save block the chain_db
                self.chain_db.post_block(block)
                # TESTING
                # print(f'Trying to post block: {block}')
                # print(f'RAW BLOCK: {block.raw_block}')
                # print(f'Decode raw block: {self.d.raw_block(block.raw_block)}')

            # Save block to mem_chain
            self.chain.append(block)

            # Adjust total_mining_amount
            self.total_mining_amount -= block.mining_tx.reward

            # Update reward
            # When loading
            if loading:
                self.load_count += 1
                if self.load_count % self.f.HALVING_NUMBER == 0:
                    self.update_reward()

            # When running
            if self.height % self.f.HALVING_NUMBER == 0 or self.mining_reward > self.total_mining_amount:
                self.update_reward()

            # Update target
            # Adjust target every heartbeat blocks
            if self.height % self.f.HEARTBEAT == 0:
                self.update_target()

            # Update mem_chain
            self.update_memchain()

            # Cleanup forks
            self.cleanup_forks()
            return True

        else:
            # Check forks
            fork_block = self.handle_fork(block)

        # Cleanup forks
        self.cleanup_forks()
        return fork_block

    def pop_block(self) -> bool:
        '''
        Will pop the last block in the chain provided it's not the genesis block
        '''
        # Don't pop the genesis block
        if self.height == 0:
            return False

        # Remove top most block from mem
        removed_block = self.chain.pop(-1)

        # Add reward
        self.total_mining_amount += removed_block.mining_tx.reward

        # Remove mining utxo from db
        self.chain_db.delete_utxo(removed_block.mining_tx.id, 0)

        # Remove output utxos and restore inputs for each transaction

        for tx in removed_block.transactions:
            # Outputs
            for utxo_output in tx.outputs:
                self.chain_db.delete_utxo(tx.id, tx.outputs.index(utxo_output))

            # Inputs
            for utxo_input in tx.inputs:
                tx_id = utxo_input.tx_id
                tx_index = utxo_input.index

                temp_tx = self.get_tx_by_id(tx_id)
                type = int(temp_tx.raw_tx[:self.f.TYPE_CHARS], 16)
                if type == self.f.MINING_TX_TYPE:
                    utxo_output = temp_tx.mining_utxo
                else:
                    utxo_output = temp_tx.outputs[tx_index]

                # Add utxo_output
                amount = utxo_output.amount
                address = utxo_output.address
                block_height = utxo_output.block_height

                # Database
                self.chain_db.post_utxo(tx_id, tx_index, UTXO_OUTPUT(amount, address, block_height))

        # Remove block from db
        self.chain_db.delete_block(self.height)

        return True

    def create_genesis_block(self) -> Block:
        genesis_transaction = MiningTransaction(0, self.f.HALVING_NUMBER * self.f.BASIC_TO_BBS, 0,
                                                Wallet(seed=0, save=False).address, 0xffffffffffffffff)
        genesis_block = Block('', self.target, self.GENESIS_NONCE, self.GENESIS_TIMESTAMP, genesis_transaction, [])

        return genesis_block

    # Fork methods

    def create_fork(self, block: Block):
        self.forks.append({
            block.mining_tx.height: block
        })
        # Logging
        print(f'FORK CREATED\n '
              f'HEIGHT: {block.mining_tx.height}\n'
              f'BLOCK ID: {block.id}')

    def handle_fork(self, block: Block) -> bool:
        # Logging
        print(f'Fork being handled. Height: {block.height}, Block  id: {block.id}')

        # Look for block with height = block.height -1
        forks_list = self.forks.copy()
        candidate_fork = None
        for dict in forks_list:
            if self.height in dict.keys():
                temp_block = dict[self.height]
                if temp_block.id == block.prev_id:
                    candidate_fork = temp_block

        # No block found, can't handle block in the forks
        if not candidate_fork:
            return False

        # Pop block and try candidate_fork
        popped_block = self.chain[-1]
        self.pop_block()
        candidate_added = self.add_block(candidate_fork)
        if candidate_added:
            latest_added = self.add_block(block)
            if latest_added:
                # Add the popped block to forks and remove the other one
                self.forks.remove({candidate_fork.mining_tx.height: candidate_fork})
                self.create_fork(popped_block)
                # Logging
                print(f'Fork handled. Height: {block.mining_tx.height}, Block  id: {block.id}')
                return True
            # Fail to add block, return to popped block
            else:
                self.pop_block()
                self.add_block(popped_block)
                return False
        # Fail to add candidate, return to popped block
        else:
            self.add_block(popped_block)
            return False

    def cleanup_forks(self):
        # If more than heartbeat # of blocks have elapsed, remove the fork
        fork_list = self.forks.copy()
        for fork_dict in fork_list:
            fork_height = list(fork_dict.keys())[0]
            if fork_height + self.heartbeat < self.height:
                self.forks.remove(fork_dict)

    # Updates
    def update_reward(self):
        # Genesis
        if self.mining_reward == 0:
            self.mining_reward = self.f.STARTING_REWARD
        # Account for near empty mine
        elif self.mining_reward > self.total_mining_amount:
            self.mining_reward = self.total_mining_amount
        # Otherwise divide by 2
        else:
            # Logging
            print(f'Height is {self.height}. Halving available reward.')
            self.mining_reward //= 2

        # Calc interest if mining_amount is zero
        if self.total_mining_amount == 0:
            # Find all utxos with block_height >= current_height + HALVING_NUMBER
            next_height = self.height + self.f.HALVING_NUMBER
            next_amount = self.chain_db.get_total_amount_greater_than_block_height(next_height)
            self.total_mining_amount = next_amount  # int(next_amount / 100)
            self.mining_reward = int(self.total_mining_amount // self.f.HALVING_NUMBER)

    def update_target(self):

        # Account for genesis
        if len(self.chain) < self.heartbeat:
            return self.target

        # Get elapsed time
        last_block_time = self.last_block.timestamp
        first_block_time = self.chain[-self.heartbeat].timestamp
        elapsed_time = last_block_time - first_block_time

        # Get absolute difference between desired time
        desired_time = self.heartbeat * self.heartbeat
        abs_diff = abs(elapsed_time - desired_time)

        # Use absolute difference to find adjust factor for target
        adjust_factor = 0
        interval = self.heartbeat
        while abs_diff > interval:
            adjust_factor += 1
            interval += self.heartbeat

        # Adjust either up or down
        if elapsed_time - desired_time > 0:  # Took longer than expected, lower target
            # Logging
            print(f'Updating target. Adjusting target down by {adjust_factor}')
            self.target = self.f.adjust_target_down(self.target, adjust_factor)
        elif elapsed_time - desired_time < 0:  # Took shorter than expected, raise target
            # Logging
            print(f'Updating target. Adjusting target up by {adjust_factor}')
            self.target = self.f.adjust_target_up(self.target, adjust_factor)

    def update_memchain(self):
        # Only keep last heartbeat blocks in mem chain and genesis block at index 0
        while len(self.chain) > self.heartbeat + 1:
            self.chain.pop(1)

    # Search methods
    def find_block_by_tx_id(self, tx_id: str):
        '''
        Will return a Block if the tx_id is in its list. Otherwise return None
        THIS IS EXPENSIVE
        TODO: Change to search through memchain first then through db
        '''
        temp_height = self.height
        block = None
        block_found = False
        while temp_height > 0 and not block_found:
            raw_block_dict = self.chain_db.get_raw_block(temp_height)
            temp_block = self.d.raw_block(raw_block_dict['raw_block'])
            if tx_id in temp_block.tx_ids:
                block = temp_block
                block_found = True
            temp_height -= 1
        return block

    def get_tx_by_id(self, tx_id: str):
        '''
        We return the Transaction object if the tx_id is in a Block
        '''
        tx = None
        temp_block = self.find_block_by_tx_id(tx_id)
        if temp_block:
            # TESTING
            # print(f'TEMP BLOCK IN GET_TX_BY_ID: {temp_block}')
            # Check for mining tx
            if temp_block.mining_tx.id == tx_id:
                tx = temp_block.mining_tx
            else:
                tx_index = temp_block.tx_ids.index(tx_id) - 1  # -1 to account for mining tx
                tx = temp_block.transactions[tx_index]
        return tx

    # Load chain
    def load_chain(self):
        # Load rest of chain if it exists
        temp_height = len(self.chain) - 1
        while temp_height != self.height:
            temp_raw_block = self.chain_db.get_raw_block(temp_height + 1)
            if temp_raw_block:
                temp_block = self.d.raw_block(temp_raw_block['raw_block'])
                if self.add_block(temp_block, loading=True):
                    temp_height += 1
                else:
                    # Logging
                    print('Error loading blocks from chain_db')
                    temp_height = self.height
