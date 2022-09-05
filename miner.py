'''
The Miner class
'''
from block import Block
import logging
from formatter import Formatter


class Miner():
    def __init__(self, logger=None):
        self.is_mining = False

        # Loggging
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel('DEBUG')

    def mine_block(self, block: Block):
        # Set mining flag
        self.is_mining = True

        # Start Mining
        self.logger.info(f'Beginning mining of block at height {block.height}')
        while int(block.id, 16) > block.target and self.is_mining:
            block.header.nonce += 1

        if self.is_mining:
            self.logger.info(f'Successfully mined block at height {block.height}')
            return block
        else:
            self.logger.info('Mining interrupt received.')
            return None

    def stop_mining(self):
        self.is_mining = False
