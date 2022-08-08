'''
The Blockchain Class
'''

from .block import Block
from .database import DataBase
from pathlib import Path
from .formatter import Formatter
from .decoder import Decoder
from .utxo import UTXO_OUTPUT
from .transactions import Transaction
from .wallet import Wallet
from .timestamp import utc_to_seconds
from basicblockchains_ecc.elliptic_curve import secp256k1


class Blockchain():
    '''
    The Blockchain will be saving data to a db, and so can be instantiated with a directory path other than default.
    Similarly, the filenames for the db can be other than default "chain.db".
    '''
    # Genesis values
    GENESIS_NONCE = 425287
    GENESIS_TIMESTAMP = 1659990618

    # Directory defaults
    DIR_PATH = './data/'
    DB_FILE = 'chain.db'

    # Decoder and formatter
    d = Decoder()
    f = Formatter()

    def __init__(self, dir_path=DIR_PATH, db_file=DB_FILE):
        # Curve for cryptography
        self.curve = secp256k1()

        # Set path and filename variables
        self.dir_path = dir_path
        self.db_file = db_file

        # Create db - Database will create file
        self.chain_db = DataBase(self.dir_path, self.db_file)

        # Mining values
        self.total_mining_amount = self.f.TOTAL_MINING_AMOUNT
        self.mining_reward = self.f.STARTING_REWARD
        self.target = self.f.target_from_parts(self.f.STARTING_TARGET_COEFFICIENT, self.f.STARTING_TARGET_EXPONENT)
        self.heartbeat = self.f.HEARTBEAT

        # Create chain list to hold last HEARTBEAT blocks
        self.chain = []

        # Create genesis block
        self.add_block(self.create_genesis_block())

        # Load rest of chain if it exists

    # Properties
    @property
    def height(self):
        return len(self.chain) - 1

    @property
    def last_block(self):
        return self.chain[-1]

    # Block methods
    def validate_block(self, block: Block) -> bool:
        # Check previous id
        if block.previous_id != self.last_block.id:
            # Logging
            return False

        # Check target
        if int(block.id) > self.target:
            # Logging
            return False

        # Check transactions
        if not block.transactions:
            # Logging - missing mining tx
            return False

        # Check mining_tx
        try:
            mining_tx = block.transactions[0]
            assert mining_tx.inputs == []
            mining_utxo = mining_tx.outputs[0]
        except IndexError:
            # Logging
            return False

        # Check mining_utxo block height
        if mining_utxo.block_height < self.height + 1 + self.f.MINING_DELAY:
            # Logging
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

        # Check fees and reward
        if fees + self.mining_reward != mining_utxo.amount:
            # Logging
            return False

        return True

    def add_block(self, block: Block):
        valid_block = False

        # Account for genesis
        if self.chain == []:
            valid_block = True
        # Check for fork
        elif block.previous_id == self.last_block.previous_id:
            self.create_fork(block)
        else:
            # Validate Block
            valid_block = self.validate_block(block)

        if valid_block:
            # Consume UTXOS
            for tx in block.transactions:
                # Consume UTXOS in tx inputs
                for utxo_input in tx.inputs:
                    self.chain_db.delete_utxo(utxo_input.tx_id, utxo_input.index)

                # Add UTXOS in tx outputs
                for utxo_output in tx.outputs:
                    self.chain_db.post_utxo(tx.id, tx.outputs.index(utxo_output), utxo_output)

            # Save block the chain_db
            self.chain_db.post_block(block, self.height + 1)

            # Save block to mem_chain
            self.chain.append(block)

            # Adjust total_mining_amount
            self.total_mining_amount -= self.mining_reward

            # Blockchain maintenance when height % heartbeat == 0

    def pop_block(self):
        pass

    def create_genesis_block(self) -> Block:
        genesis_utxo_output = UTXO_OUTPUT(self.mining_reward, Wallet(seed=0).address, 0xffffffffffffffff)
        genesis_transaction = Transaction(inputs=[], outputs=[genesis_utxo_output])
        genesis_block = Block('', self.target, self.GENESIS_NONCE, self.GENESIS_TIMESTAMP, [genesis_transaction])

        # Verify
        assert int(genesis_block.id, 16) < self.target

        return genesis_block

    # Create fork

    def create_fork(self, block: Block):
        pass


