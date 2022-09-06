'''
The Miner class
'''
from block import Block
import logging
from logging.handlers import QueueHandler
from formatter import Formatter
from multiprocessing import Queue


class Miner():
    def __init__(self):
        self.is_mining = False

    def mine_block(self, block: Block):
        # Set mining flag
        self.is_mining = True

        while int(block.id, 16) > block.target and self.is_mining:
            block.header.nonce += 1

        if self.is_mining:
            return block
        else:
            return None

    def stop_mining(self):
        self.is_mining = False
