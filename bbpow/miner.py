'''
The Miner class
'''
from .block import Block


# --- MINE BLOCK METHOD --- #

def mine_a_block(block: Block, queue=None):
    while int(block.id, 16) > block.target:
        block.header.nonce += 1

    if queue:
        queue.put(block)
    else:
        return block
