'''
The Transactions class
'''
from .utxo import UTXO_OUTPUT, UTXO_INPUT
import json
from hashlib import sha256


class Transaction():
    '''
    Transactions are instantiated with a list of utxo_inputs and utxo_outputs
    '''

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
    def id(self):
        return sha256(self.to_json.encode()).hexdigest()
