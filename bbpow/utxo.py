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
        # Setup formatter
        f = Formatter()

        # Type version
        type = format(f.UTXO_INPUT_TYPE, f'0{f.TYPE_CHARS}x')
        version = f.VERSION

        # Input values - signature already formatted
        tx_id = format(int(self.tx_id, 16), f'0{f.HASH_CHARS}x')
        index = format(self.index, f'0{f.INDEX_CHARS}x')

        # Raw = type + version + tx_id + index + signature
        return type + version + tx_id + index + self.signature

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
        # Setup formatter
        f = Formatter()

        # Type version
        type = format(f.UTXO_OUTPUT_TYPE, f'0{f.TYPE_CHARS}x')
        version = f.VERSION

        # Format values
        amount = format(self.amount, f'0{f.AMOUNT_CHARS}x')
        address = f.hex_address(self.address)
        block_height = format(self.block_height, f'0{f.HEIGHT_CHARS}x')

        # Raw = type + version + amount + address + block_height
        return type + version + amount + address + block_height

    @property
    def id(self):
        return sha256(self.raw_utxo.encode()).hexdigest()
