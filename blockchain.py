'''
The Blockchain Class
'''

import logging

from basicblockchains_ecc.elliptic_curve import secp256k1

from block import Block
from database import DataBase
from decoder import Decoder
from formatter import Formatter
from transactions import MiningTransaction
from wallet import Wallet


class Blockchain():
    '''
    The Blockchain will be saving data to a db, and so can be instantiated with a directory path other than default.
    Similarly, the filenames for the db can be other than default "chain.db".
    '''
    # GENESIS CONSTANTS
    GENESIS_NONCE = 325915  # Tuned to production values in Formatter
    GENESIS_TIMESTAMP = 1666373400  # Friday, October 21, 2022 1:30:00 PM GMT-05:00

    # Directory defaults
    DIR_PATH = 'data/'
    DB_FILE = 'chain.db'

    # Decoder and formatter
    d = Decoder()
    f = Formatter()

    def __init__(self, dir_path=DIR_PATH, db_file=DB_FILE, logger=None):
        # Logging
        if logger:
            self.logger = logger.getChild('Blockchain')
        else:
            self.logger = logging.getLogger('Blockchain')
            self.logger.setLevel('DEBUG')
            self.logger.addHandler(logging.StreamHandler())

        self.logger.debug(f'Logger instantiated in blockchain with name: {self.logger.name}')

        # Curve for cryptography
        self.curve = secp256k1()

        # Fixed heartbeat for Blockchain
        self.heartbeat = self.f.HEARTBEAT

        # --- Initial dynamic Blockchain values --- #
        self.total_mining_amount = self.f.TOTAL_MINING_AMOUNT
        self.mining_reward = 0
        self.target = self.f.target_from_parts(self.f.STARTING_TARGET_COEFFICIENT, self.f.STARTING_TARGET_EXPONENT)
        self.height = -1

        # Create chain list to hold last HEARTBEAT blocks
        self.chain = []

        # Create fork list to index forked blocks
        self.forks = []

        # Set path and filename variables
        self.dir_path = dir_path
        self.db_file = db_file

        # Create db - Database will create file in the given dir_path even if it doesn't exist
        self.chain_db = DataBase(self.dir_path, self.db_file)

        # Start new chain or load from db
        db_height = self.chain_db.get_height()['height']
        if db_height == -1:
            self.add_block(self.create_genesis_block(), loading=False)
        else:
            self.add_block(self.create_genesis_block(), loading=True)
            self.load_chain()

    # --- PROPERTIES --- #
    @property
    def last_block(self):
        return self.chain[-1]

    # --- BLOCK METHODS --- #

    def validate_block(self, block: Block) -> bool:
        # Check previous id
        if block.prev_id != self.last_block.id:
            # Logging
            self.logger.warning('Block failed validation. Block.prev_id != last_block.id')
            return False

        # Check target
        if int(block.id, 16) > self.target:
            # Logging
            self.logger.warning('Block failed validation. Block id bigger than target')
            return False

        # Check Mining Tx height
        if block.height != self.last_block.height + 1:
            # Logging
            self.logger.warning('Block failed validation. Mining_tx height incorrect')
            return False

        # Check Mining UTXO block_height
        if block.mining_tx.mining_utxo.block_height < self.last_block.height + 1 + self.f.MINING_DELAY:
            # Logging
            self.logger.warning('Block failed validation. Mining tx block height incorrect')
            return False

        # Check fees + reward = amount in mining_utxo
        block_total = block.mining_tx.block_fees + block.mining_tx.reward
        if block_total != block.mining_tx.mining_utxo.amount:
            # Logging
            self.logger.warning('Block failed validation. Block total incorrect')
            return False

        # Make sure timestamp is increasing
        if block.timestamp <= self.last_block.timestamp:
            # Logging
            self.logger.warning('Block failed validation. Block time too early.')
            return False

        # Make sure timestamp isn't too far ahead
        if block.timestamp > self.last_block.timestamp + pow(self.heartbeat, 2):
            # Logging
            self.logger.warning('Block timestamp too far ahead.')
            return False

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

                # Return False if dict is empty
                if not utxo_dict:
                    # Logging
                    self.logger.warning(
                        f'Utxo output with tx_id {tx_id} and index {index} does not exist in the database.')
                    return False

                # Verify address
                utxo_address = utxo_dict['address']
                temp_address = self.f.address(cpk)
                if temp_address != utxo_address:
                    # Logging
                    self.logger.warning(
                        f'Address in utxo {utxo_address} does not match address generated from signature: {temp_address}')
                    return False

                # Verify signature
                if not self.curve.verify_signature(ecdsa_tuple, tx_id, self.curve.decompress_point(cpk)):
                    # Logging
                    self.logger.warning('Decoded signature fails to verify against cryptographic curve.')
                    return False

                # Update amount
                input_amount += utxo_dict['amount']

            for output_utxo in tx.outputs:
                output_amount += output_utxo.amount

            # Check input_amount >= output_amount
            if input_amount < output_amount:
                # Logging
                self.logger.warning(
                    f'Input amount in transactions {input_amount}; greater than output amount in transactions {output_amount}')
                return False

            fees += input_amount - output_amount

        # Verify fees in block_transactions agrees with MiningTx
        if fees != block.mining_tx.block_fees:
            # Logging
            self.logger.warning(
                f'Validation fails. Block fees incorrect. Calculated fees{fees}; mining tx fees {block.mining_tx.block_fees}')
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
                # Logging
                self.logger.info(f'Successfully added block with id {block.id} at height {block.height}')
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

            # Save block to mem_chain
            self.chain.append(block)

            # Adjust height
            self.height += 1

            # Adjust total_mining_amount
            self.total_mining_amount -= block.mining_tx.reward

            # Update reward
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

        # Adjust height
        self.height -= 1

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

                # Database
                self.chain_db.post_utxo(tx_id, tx_index, utxo_output)

        # Remove block from db
        self.chain_db.delete_block()

        # Insert block at height self.height - self.heartbeat if it exists
        if len(self.chain) < self.heartbeat + 1 and self.height > self.heartbeat:
            raw_block_dict = self.chain_db.get_raw_block(self.height - self.heartbeat)
            if raw_block_dict:
                self.chain.insert(1, self.d.raw_block(raw_block_dict['raw_block']))

        # Logging
        self.logger.debug(f'Successfully removed block at height {self.height + 1}')
        return True

    def create_genesis_block(self) -> Block:
        genesis_transaction = MiningTransaction(0, self.f.HALVING_NUMBER * self.f.BASIC_TO_BBS, 0,
                                                Wallet(seed=0, save=False, logger=self.logger).address,
                                                0xffffffffffffffff)

        genesis_block = Block('', self.target, self.GENESIS_NONCE, self.GENESIS_TIMESTAMP, genesis_transaction, [])
        return genesis_block

    # --- FORK METHODS --- #

    def create_fork(self, block: Block):
        fork_dict = {block.height: block.raw_block}
        if fork_dict not in self.forks:
            self.forks.append(fork_dict)
            # Logging
            self.logger.info(f'Fork created at height {block.height} for block with id {block.id}')
        else:
            # Logging
            self.logger.info(f'Block with height {block.height} and id {block.id} already in forks.')

    def handle_fork(self, block: Block) -> bool:
        # Logging
        self.logger.info(f'Fork being handled. Height: {block.height}, Block  id: {block.id}')

        # Look for block with height = block.height -1
        forks_list = self.forks.copy()
        candidate_fork = None
        for dict in forks_list:
            if self.height in dict.keys():
                temp_block = self.d.raw_block(dict[self.height])
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
                self.forks.remove({candidate_fork.height: candidate_fork.raw_block})
                self.create_fork(popped_block)
                # Logging
                self.logger.info(f'Fork handled. Height: {block.height}, Block  id: {block.id}')
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

    # --- UPDATES --- #
    def update_reward(self):
        # Genesis
        if self.mining_reward == 0:
            self.mining_reward = self.f.STARTING_REWARD
            # Logging
            self.logger.debug(f'Setting initial mining reward to {self.mining_reward}')
        # Account for near empty mine
        elif self.mining_reward > self.total_mining_amount:
            self.mining_reward = self.total_mining_amount
        # Otherwise divide by 2
        else:
            # Logging
            self.logger.info(f'Height is {self.height}. Halving available reward.')
            self.mining_reward //= 2

        # Calc interest if mining_amount is zero
        if self.total_mining_amount == 0:
            # Find all utxos with block_height >= current_height + HALVING_NUMBER
            next_height = self.height + self.f.HALVING_NUMBER
            next_amount = self.chain_db.get_invested_amount(next_height)
            self.total_mining_amount = next_amount
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
        desired_time = pow(self.heartbeat, 2)
        abs_diff = abs(elapsed_time - desired_time)

        # Logging
        self.logger.info(f'Total time (in seconds) between saving last {self.heartbeat} blocks: {elapsed_time}')
        self.logger.info(f'Desired time (in seconds) to mine and save {self.heartbeat} blocks: {desired_time}')
        self.logger.info(f'Difference in total and desired time: {elapsed_time - desired_time}')

        # Adjust either up or down
        if elapsed_time - desired_time > 0:  # Took longer than expected, raise target | higher target = easier
            # Logging
            self.logger.info(f'Updating target. Adjusting target up by {abs_diff}')
            self.target = self.f.adjust_target_up(self.target, abs_diff)
        elif elapsed_time - desired_time < 0:  # Took shorter than expected, lower target | lower target = harder
            # Logging
            self.logger.info(f'Updating target. Adjusting target down by {abs_diff}')
            self.target = self.f.adjust_target_down(self.target, abs_diff)

    def update_memchain(self):
        # Only keep last heartbeat blocks in mem chain and genesis block at index 0
        while len(self.chain) > self.heartbeat + 1:
            self.chain.pop(1)

    # --- SEARCH METHODS --- #
    def find_block_by_tx_id(self, tx_id: str):
        '''
        Will return a Block if the tx_id is in its list. Otherwise, return None
        Searches through db.
        '''
        temp_height = self.height
        block = None
        block_found = False

        while temp_height > -1 and not block_found:
            # Search through database
            raw_block_dict = self.chain_db.get_raw_block(temp_height)
            if raw_block_dict != {}:
                temp_block = self.d.raw_block(raw_block_dict['raw_block'])
            else:
                # Return None if no block is at that height
                return None

            # Search for tx_id in Block
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
            # Check for mining tx
            if temp_block.mining_tx.id == tx_id:
                tx = temp_block.mining_tx
            else:
                tx_index = temp_block.tx_ids.index(tx_id) - 1  # -1 to account for mining tx
                tx = temp_block.transactions[tx_index]
        return tx

    # --- LOAD CHAIN --- #
    def load_chain(self):
        '''
        If we are loading the chain, then the db is not available to be written to yet. Hence, we are not concerned
        with any DB locking operational errors, so db statements are not enclosed in a try/catch block.
        '''
        self.logger.info(f'Loading blockchain from database.')

        # Get height
        db_height = self.chain_db.get_height()['height']

        while self.height < db_height:
            raw_block_dict = self.chain_db.get_raw_block(self.height + 1)
            if raw_block_dict:
                added = self.add_block(self.d.raw_block(raw_block_dict['raw_block']), loading=True)
                if not added:
                    # Logging
                    self.logger.critical(f'Error loading raw block from db at height {self.height + 1}')
                    break
            else:
                self.logger.critical(f'No raw block returned at height {self.height + 1}')
                break

        self.logger.info(f'Successfully loaded Blockchain from database. Current height: {self.height}')
