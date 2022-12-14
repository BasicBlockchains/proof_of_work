'''
Decoder - decodes various formatted data structs
'''
import logging
from hashlib import sha256

from basicblockchains_ecc.elliptic_curve import secp256k1

from block import Block
from formatter import Formatter
from headers import Header
from transactions import Transaction, MiningTransaction
from utxo import UTXO_INPUT, UTXO_OUTPUT


class Decoder:
    F = Formatter()
    t_index = F.TYPE_CHARS
    v_index = t_index + F.VERSION_CHARS

    def __init__(self, logger=None):
        # Loggging
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel('DEBUG')

    # Verify type version
    def verify_type_version(self, data_type: int, data_version: str, raw_data: str) -> bool:
        # Type and version
        type = int(raw_data[:self.t_index], 16)
        version = raw_data[self.t_index:self.v_index]

        try:
            assert type == data_type
            assert version == data_version
            assert data_version in self.F.ACCEPTED_VERSIONS
        except AssertionError:
            # Logging
            self.logger.error(f'Type/version error when decoding raw data. Type: {type}, data_type: {data_type}')
            return False
        return True

    # CPK, Signature, Address
    def decode_cpk(self, cpk: str) -> tuple:
        '''
        The cpk is a hex string - this may or may not have a leading '0x' indicator.
        Hence, we obtain the x point first by moving from EOS backwards, then what's left is parity integer.
        '''
        parity = int(cpk[:-self.F.HASH_CHARS], 16) % 2
        x = int(cpk[-self.F.HASH_CHARS:], 16)

        curve = secp256k1()

        # Check x
        try:
            assert curve.is_x_on_curve(x)
        except AssertionError:
            # Logging
            self.logger.error('x not on curve')
            return (None,)

        # Get y
        temp_y = curve.find_y_from_x(x)

        # Check parity
        y = temp_y if temp_y % 2 == parity else curve.p - temp_y

        # Check point
        try:
            assert curve.is_point_on_curve((x, y))
        except AssertionError:
            # Logging
            self.logger.error('Point not on curve')
            return (None,)
        # Return point
        return (x, y)

    def decode_signature(self, signature: str):
        # Type version
        if not self.verify_type_version(self.F.SIGNATURE_TYPE, self.F.VERSION, signature):
            # Logging
            self.logger.error('Type/Version error in raw utxo_input')
            return None

        # Indexing

        start_index = self.F.TYPE_CHARS + self.F.VERSION_CHARS
        cpk_index = start_index + self.F.CPK_CHARS
        r_index = cpk_index + self.F.HASH_CHARS
        s_index = r_index + self.F.HASH_CHARS

        # Values
        cpk = '0x' + signature[start_index:cpk_index]
        r = int(signature[cpk_index:r_index], 16)
        s = int(signature[r_index:s_index], 16)

        # Return cpk and ecdsa tuple
        return cpk, (r, s)

    def verify_address(self, address: str) -> bool:
        '''
        We decode from base58 and verify that the epk generates the expected checksum.
        Leading 0 loss may occur going from str to int - we remove the type/version and checksum and what remains is epk.
        '''
        # First get hex value - remove leading '0x'
        hex_addy = hex(self.F.base58_to_int(address))[2:]

        # Verify type/version
        type = int(hex_addy[:self.F.TYPE_CHARS], 16)

        try:
            assert type == self.F.ADDRESS_TYPE
        except AssertionError:
            # Logging
            self.logger.error('Address has incorrect type')
            return False

        # Indexing
        start_index = self.F.TYPE_CHARS
        end_index = -self.F.CHECKSUM_CHARS

        epk = hex_addy[start_index:end_index]
        checksum = hex_addy[end_index:]

        while len(epk) != self.F.EPK_CHARS:
            epk = '0' + epk

        return sha256(
            sha256(epk.encode()).hexdigest().encode()
        ).hexdigest()[:self.F.CHECKSUM_CHARS] == checksum

    def verify_signature(self, signature: str, tx_id: str):
        # Get signature parts
        cpk, ecdsa_tuple = self.decode_signature(signature)

        # Verify address
        curve = secp256k1()
        return curve.verify_signature(ecdsa_tuple, tx_id, curve.decompress_point(cpk))

    # UTXOS
    def raw_utxo_input(self, raw_utxo: str):
        # Type version
        if not self.verify_type_version(self.F.UTXO_INPUT_TYPE, self.F.VERSION, raw_utxo):
            # Logging
            self.logger.error('Type/Version error in raw utxo_input')
            return None

        # tx_id, tx_index, signature
        index0 = self.v_index
        index1 = index0 + self.F.HASH_CHARS
        index2 = index1 + self.F.INDEX_CHARS
        index3 = index2 + self.F.SIGNATURE_CHARS

        tx_id = raw_utxo[index0:index1]
        tx_index = int(raw_utxo[index1:index2], 16)
        signature = raw_utxo[index2:index3]

        return UTXO_INPUT(tx_id, tx_index, signature)

    def raw_utxo_output(self, raw_utxo: str):
        # Type version
        if not self.verify_type_version(self.F.UTXO_OUTPUT_TYPE, self.F.VERSION, raw_utxo):
            # Logging
            self.logger.error('Type/Version error in raw utxo_output')
            return None

        # tx_id, tx_index, signature
        index0 = self.v_index
        index1 = index0 + self.F.AMOUNT_CHARS
        index2 = index1 + self.F.ADDRESS_CHARS
        index3 = index2 + self.F.HEIGHT_CHARS

        amount = int(raw_utxo[index0:index1], 16)
        address = self.F.int_to_base58(int(raw_utxo[index1:index2], 16))
        block_height = int(raw_utxo[index2:index3], 16)

        return UTXO_OUTPUT(amount, address, block_height)

    # Transaction
    def raw_transaction(self, raw_tx: str):
        # Type version
        if not self.verify_type_version(self.F.TX_TYPE, self.F.VERSION, raw_tx):
            # Logging
            self.logger.error('Type/Version error in raw transaction')
            return None

        temp_index = self.v_index + self.F.COUNT_CHARS

        # Get inputs
        input_count = int(raw_tx[self.v_index:temp_index], 16)
        inputs = []
        for x in range(input_count):
            utxo_input = self.raw_utxo_input(raw_tx[temp_index:])
            inputs.append(utxo_input)
            temp_index += len(utxo_input.raw_utxo)

        # Get outputs
        output_count = int(raw_tx[temp_index:temp_index + self.F.COUNT_CHARS], 16)
        outputs = []
        temp_index += self.F.COUNT_CHARS
        for y in range(output_count):
            utxo_output = self.raw_utxo_output(raw_tx[temp_index:])
            outputs.append(utxo_output)
            temp_index += len(utxo_output.raw_utxo)

        # Return Transaction
        return Transaction(inputs, outputs)

    def raw_mining_transaction(self, raw_tx: str):
        # Type version
        if not self.verify_type_version(self.F.MINING_TX_TYPE, self.F.VERSION, raw_tx):
            # Logging
            self.logger.error('Type/Version error in raw mininig transaction')
            return None

        # Indexing
        index0 = self.v_index
        index1 = index0 + self.F.HEIGHT_CHARS
        index2 = index1 + self.F.REWARD_CHARS
        index3 = index2 + self.F.AMOUNT_CHARS

        # Values
        height = int(raw_tx[index0:index1], 16)
        reward = int(raw_tx[index1:index2], 16)
        block_fees = int(raw_tx[index2:index3], 16)

        # Mining UTXO
        mining_utxo = self.raw_utxo_output(raw_tx[index3:])
        try:
            address = mining_utxo.address
            return MiningTransaction(height, reward, block_fees, address, mining_utxo.block_height)
        except AttributeError:
            # Logging
            self.logger.error(f'Mining utxo failed to return raw_utxo_output from {raw_tx[index3:]}')

        return None

    def transaction_from_dict(self, tx_dict: dict):
        input_count = tx_dict['input_count']
        inputs = []
        for y in range(input_count):
            input_dict = tx_dict[f'input_{y}']
            tx_id = input_dict['tx_id']
            tx_index = input_dict['index']
            signature = input_dict['signature']
            inputs.append(UTXO_INPUT(tx_id, tx_index, signature))
        output_count = tx_dict['output_count']
        outputs = []
        for z in range(output_count):
            output_dict = tx_dict[f'output_{z}']
            amount2 = output_dict['amount']
            address2 = output_dict['address']
            block_height2 = output_dict['block_height']
            outputs.append(UTXO_OUTPUT(amount2, address2, block_height2))
        return Transaction(inputs, outputs)

    # Block
    def raw_block(self, raw_block: str):
        # Type version
        if not self.verify_type_version(self.F.BLOCK_TYPE, self.F.VERSION, raw_block):
            # Logging
            self.logger.error('Type/Version error in raw block')
            return None

        # Headers
        header = self.raw_block_header(raw_block[self.v_index:self.v_index + self.F.HEADER_CHARS])
        mining_tx, transactions = self.raw_block_transactions(raw_block[self.v_index + self.F.HEADER_CHARS:])

        # Get block and verify merkle root
        block = Block(header.prev_id, header.target, header.nonce, header.timestamp, mining_tx, transactions)
        if block.merkle_root != header.merkle_root:
            # Logging
            self.logger.error('Merkle root error when recreating block from raw')
            return None
        return block

    def raw_block_header(self, raw_header: str):
        # Type version
        if not self.verify_type_version(self.F.HEADER_TYPE, self.F.VERSION, raw_header):
            # Logging
            self.logger.error('Type/Version error in raw block headers')
            return None

        # Indexing
        index0 = self.v_index
        index1 = index0 + self.F.HASH_CHARS
        index2 = index1 + self.F.HASH_CHARS
        index3 = index2 + self.F.TARGET_CHARS
        index4 = index3 + self.F.NONCE_CHARS
        index5 = index4 + self.F.TIMESTAMP_CHARS

        # Recover values
        prev_id = raw_header[index0:index1]
        merkle_root = raw_header[index1:index2]
        target = self.F.int_from_target(raw_header[index2:index3])
        nonce = int(raw_header[index3:index4], 16)
        timestamp = int(raw_header[index4:index5], 16)

        # Return header
        return Header(prev_id, merkle_root, target, nonce, timestamp)

    def raw_block_transactions(self, raw_txs: str):
        # Type version
        if not self.verify_type_version(self.F.BLOCK_TX_TYPE, self.F.VERSION, raw_txs):
            # Logging
            self.logger.error('Type/Version error in raw block transactions')
            return None

            # Get mining_tx
        mining_tx = self.raw_mining_transaction(raw_txs[self.v_index:])

        # Indexing
        mining_index = self.v_index + len(mining_tx.raw_tx)
        count_index = self.F.BLOCK_TX_CHARS + mining_index
        tx_count = int(raw_txs[mining_index: count_index], 16)

        # Get UserTx's
        transactions = []
        temp_index = count_index
        for x in range(0, tx_count):
            new_tx = self.raw_transaction(raw_txs[temp_index:])
            transactions.append(new_tx)
            temp_index += len(new_tx.raw_tx)

        # Return MiningTx, and UserTx list
        return mining_tx, transactions
