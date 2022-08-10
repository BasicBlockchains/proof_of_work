'''
The Miner class
'''
from .block import Block


class Miner():
    def __init__(self):
        self.is_mining = False

    def mine_block(self, block: Block):
        # Set mining flag
        self.is_mining = True

        # Start Mining
        while int(block.id, 16) > block.target and self.is_mining:
            block.nonce += 1
            print(f'Current block id: {block.id}', end='\r')

        if self.is_mining:
            return block
        else:
            return None

    def stop_mining(self):
        self.is_mining = False
