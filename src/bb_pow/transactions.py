'''
The Transactions class
'''
from .utxo import UTXO_OUTPUT, UTXO_INPUT
import json
from hashlib import sha256
from .formatter import Formatter
from .utxo import UTXO_OUTPUT


class MiningTransaction():
    '''
    Every block must contain a MiningTransaction. We create the class instead of Transaction for ease of use.
    '''
    # Formatter
    f = Formatter()

    def __init__(self, height: int, reward: int, block_fees: int, address: str):
        self.height = height
        self.reward = reward
        self.block_fees = block_fees
        self.mining_utxo = UTXO_OUTPUT(self.reward + self.block_fees, address, self.height + self.f.MINING_DELAY)

    def __repr__(self):
        return self.to_json

    @property
    def to_json(self):
        mining_dict = {
            "height": self.height,
            "reward": self.reward,
            "block_fees": self.block_fees,
            "mining_utxo": json.dumps(json.loads(self.mining_utxo.to_json))
        }
        return json.dumps(mining_dict)

    @property
    def raw_tx(self):
        return self.f.mining_tx(self.height, self.reward, self.block_fees, self.mining_utxo.address)

    @property
    def id(self):
        return sha256(self.raw_tx.encode()).hexdigest()


class Transaction():
    '''
    Transactions are instantiated with a list of utxo_inputs and utxo_outputs
    '''
    # Formatter
    f = Formatter()

    def __init__(self, inputs: list, outputs: list):
        self.inputs = inputs
        self.outputs = outputs

        self.input_count = len(self.inputs)
        self.output_count = len(self.outputs)

    def __repr__(self):
        return self.to_json

    @property
    def to_json(self):
        tx_dict = {'input_count': self.input_count}
        for utxo_input in self.inputs:
            tx_dict.update({f'input_{self.inputs.index(utxo_input)}': json.loads(utxo_input.to_json)})

        tx_dict.update({'output_count': self.output_count})
        for utxo_output in self.outputs:
            tx_dict.update({f'output_{self.outputs.index(utxo_output)}': json.loads(utxo_output.to_json)})

        return json.dumps(tx_dict)

    @property
    def raw_tx(self):
        return self.f.transaction(self.inputs, self.outputs)

    @property
    def id(self):
        return sha256(self.raw_tx.encode()).hexdigest()
