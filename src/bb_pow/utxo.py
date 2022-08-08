'''
The UTXO classes
'''
import json
from hashlib import sha256

from .formatter import Formatter


class UTXO_INPUT():
    '''
    The UTXO INPUT will reference an existing UTXO_OUTPUT by tx_id
    '''
    # Setup formatter
    f = Formatter()

    def __init__(self, tx_id: str, index: int, signature: str):
        self.tx_id = tx_id
        self.index = index
        self.signature = signature

    def __repr__(self):
        return self.to_json

    @property
    def to_json(self):
        return json.dumps({
            "tx_id": self.tx_id,
            "index": self.index,
            "signature": self.signature
        })

    @property
    def raw_utxo(self):
        return self.f.utxo_input(self.tx_id, self.index, self.signature)

    @property
    def id(self):
        return sha256(self.raw_utxo.encode()).hexdigest()


class UTXO_OUTPUT():
    '''
    The UTXO output will contain an amount, an address and a block_height where the amount can first be used.
    Block_height = 0 by default (used for Mining Outputs)
    '''
    # Setup formatter
    f = Formatter()

    def __init__(self, amount: int, address: str, block_height=0):
        self.amount = amount
        self.address = address
        self.block_height = block_height

    def __repr__(self):
        return self.to_json

    @property
    def to_json(self):
        return json.dumps({
            'amount': self.amount,
            'address': self.address,
            'block_height': self.block_height
        })

    @property
    def raw_utxo(self):
        return self.f.utxo_output(self.amount, self.address, self.block_height)

    @property
    def id(self):
        return sha256(self.to_json.encode()).hexdigest()
