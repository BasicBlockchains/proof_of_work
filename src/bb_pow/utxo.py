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

        # Format tx_id, index - signature assumed to be formatted properly
        tx_id = f.format_hex(self.tx_id, f.HASH_CHARS)
        index = f.format_int(self.index, f.INDEX_CHARS)

        # Format type and version
        type = f.format_int(f.UTXO_INPUT_TYPE, f.TYPE_CHARS)
        version = f.format_int(f.VERSION, f.VERSION_CHARS)

        # raw
        return type + version + tx_id + index + self.signature

    @property
    def id(self):
        return sha256(self.raw_utxo.encode()).hexdigest()


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

        # format utxo values
        amount = f.format_int(self.amount, f.AMOUNT_CHARS)
        address = f.format_hex(hex(f.base58_to_int(self.address)), f.ADDRESS_CHARS)
        block_height = f.format_int(self.block_height, f.HEIGHT_CHARS)

        # format type and version
        type = f.format_int(f.UTXO_OUTPUT_TYPE, f.TYPE_CHARS)
        version = f.format_int(f.VERSION, f.VERSION_CHARS)

        # Raw
        return type + version + amount + address + block_height

    @property
    def id(self):
        return sha256(self.to_json.encode()).hexdigest()
