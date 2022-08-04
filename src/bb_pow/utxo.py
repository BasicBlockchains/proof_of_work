'''
The UTXO classes
'''
import json
from .wallet import Wallet
from hashlib import sha256


class UTXO_INPUT():
    '''
    The UTXO INPUT will reference an existing UTXO_OUTPUT by tx_id
    '''

    def __init__(self, tx_id: str, index: int, signature: str):
        self.tx_id = tx_id
        self.index = index
        self.signature = signature

    def __repr__(self):
        utxo_dict = {
            "tx_id": self.tx_id,
            "index": self.index,
            "signature": self.signature
        }
        return json.dumps(utxo_dict)

    @property
    def id(self):
        return sha256(str(self).encode()).hexdigest()


class UTXO_OUTPUT():
    '''
    The UTXO output will contain an amount, an address and a block_height where the amount can first be used.
    Block_height = 0 by default (used for Mining Outputs)
    '''

    def __init__(self, amount: int, address: str, block_height=0):
        self.amount = amount
        self.address = address
        self.block_height = block_height

    def __repr__(self):
        utxo_dict = {
            'amount': self.amount,
            'address': self.address,
            'block_height': self.block_height
        }
        return json.dumps(utxo_dict)

    @property
    def id(self):
        return sha256(str(self).encode()).hexdigest()