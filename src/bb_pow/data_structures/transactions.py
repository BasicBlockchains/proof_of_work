'''
The Transactions class
'''
import json
from hashlib import sha256
from src.bb_pow.data_format.formatter import Formatter
from src.bb_pow.data_structures.utxo import UTXO_OUTPUT


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
            "mining_utxo": json.loads(self.mining_utxo.to_json)
        }
        return json.dumps(mining_dict)

    @property
    def raw_tx(self):
        # Setup formatter
        f = Formatter()

        # Type/version
        type = format(f.MINING_TX_TYPE, f'0{f.TYPE_CHARS}x')
        version = format(f.VERSION, f'0{f.VERSION_CHARS}x')

        # Block info
        height = format(self.height, f'0{f.HEIGHT_CHARS}x')
        reward = format(self.reward, f'0{f.REWARD_CHARS}x')
        block_fees = format(self.block_fees, f'0{f.AMOUNT_CHARS}x')

        # Raw = type + version + block_info + mining_utxo
        return type + version + height + reward + block_fees + self.mining_utxo.raw_utxo

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
        # Setup formatter
        f = Formatter()

        # Type/version
        type = format(f.TX_TYPE, f'0{f.TYPE_CHARS}x')
        version = format(f.VERSION, f'0{f.VERSION_CHARS}x')

        # Format counts
        input_count = format(self.input_count, f'0{f.COUNT_CHARS}x')
        output_count = format(self.output_count, f'0{f.COUNT_CHARS}x')

        # Format input string
        input_string = ''
        for i in self.inputs:
            input_string += i.raw_utxo

        # Format output string
        output_string = ''
        for t in self.outputs:
            output_string += t.raw_utxo

        # Raw = type + version + input_count + inputs + output_count + output
        return type + version + input_count + input_string + output_count + output_string

    @property
    def id(self):
        return sha256(self.raw_tx.encode()).hexdigest()
