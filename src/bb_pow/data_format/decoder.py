'''
Decoder - decodes various formatted data structs
'''
import json
from hashlib import sha256

from basicblockchains_ecc.elliptic_curve import secp256k1

from ..data_format.formatter import Formatter
from ..data_structures.block import Block
from ..data_structures.transactions import Transaction, MiningTransaction
from ..data_structures.utxo import UTXO_INPUT, UTXO_OUTPUT


class Decoder:
    F = Formatter()
    t_index = F.TYPE_CHARS
    v_index = t_index + F.VERSION_CHARS

    # Verify type version
    def verify_type_version(self, data_type: int, data_version: int, raw_data: str) -> bool:
        # Type and version
        type = int(raw_data[:self.t_index], 16)
        version = int(raw_data[self.t_index:self.v_index], 16)

        try:
            assert type == data_type
            assert version == data_version
            assert data_version in self.F.ACCEPTED_VERSIONS
        except AssertionError:
            # Logging
            print('Type/version error when decoding raw data.')
            print(f'Type: {type}, data_type: {data_type}')
            print(f'Version: {version}, data_version: {data_version}')
            print(f'Raw Data: {raw_data}')
            return False
        return True

    # # Decode target
    # def int_from_target(self, encoded_target: str):
    #     # Index
    #     coeff_index = self.F.TARGET_COEFFICIENT_CHARS
    #     exp_index = self.F.TARGET_EXPONENT_CHARS + coeff_index
    #
    #     coeff = int(encoded_target[:coeff_index], 16)
    #     exp = int(encoded_target[coeff_index:exp_index], 16)
    #
    #     return coeff * pow(2, 8 * (exp - 3))

    ##CPK, Signature, Address

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
            print('x not on curve')
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
            print('Point not on curve')
            return (None,)
        # Return point
        return (x, y)

    def decode_signature(self, signature: str):
        # Type version
        if not self.verify_type_version(self.F.SIGNATURE_TYPE, self.F.VERSION, signature):
            # Logging
            print('Type/Version error in raw utxo_input')
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

    def signature_json(self, signature: str):
        cpk, (r, s) = self.decode_signature(signature)
        signature_dict = {
            "compressed_public_key": cpk,
            "r": hex(r),
            "s": hex(s)
        }
        return json.dumps(signature_dict)

    def verify_address(self, address: str) -> bool:
        '''
        We decode from base58 and verify that the epk generates the expected checksum.
        Leading 0 loss may occur going from str to int - we remove the type/version and checksum and what remains is epk.
        '''
        # First get hex value - remove leading '0x'
        hex_addy = hex(self.F.base58_to_int(address))[2:]

        # Verify type/version
        type = int(hex_addy[:self.F.TYPE_CHARS], 16)
        version = int(hex_addy[self.F.TYPE_CHARS:self.F.TYPE_CHARS + self.F.VERSION_CHARS], 16)

        try:
            assert type == self.F.ADDRESS_TYPE
            assert version in self.F.ACCEPTED_VERSIONS
        except AssertionError:
            # Logging
            print('Address has incorrect type and/or version')
            return False

        # Indexing
        start_index = self.F.TYPE_CHARS + self.F.VERSION_CHARS
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
            print('Type/Version error in raw utxo_input')
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
            print('Type/Version error in raw utxo_output')
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
            print('Type/Version error in raw transaction')
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
            print('Type/Version error in raw mininig transaction')
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
        address = mining_utxo.address

        return MiningTransaction(height, reward, block_fees, address, mining_utxo.block_height)

    # Block
    def raw_block(self, raw_block: str):
        # Type version
        if not self.verify_type_version(self.F.BLOCK_TYPE, self.F.VERSION, raw_block):
            # Logging
            print('Type/Version error in raw block')
            return None

        # Headers
        header_dict = self.raw_block_header(raw_block[self.v_index:self.v_index + self.F.HEADER_CHARS])
        mining_tx, transactions = self.raw_block_transactions(raw_block[self.v_index + self.F.HEADER_CHARS:])

        # Get header values
        prev_id = header_dict['prev_id']
        merkle_root = header_dict['merkle_root']
        target = header_dict['target']
        nonce = header_dict['nonce']
        timestamp = header_dict['timestamp']

        # Get block and verify merkle root
        block = Block(prev_id, target, nonce, timestamp, mining_tx, transactions)
        if block.merkle_root != merkle_root:
            # Logging
            print('Merkle root error when recreating block from raw')
            return None
        return block

    def raw_block_header(self, raw_header: str):
        # Type version
        if not self.verify_type_version(self.F.BLOCK_HEADER_TYPE, self.F.VERSION, raw_header):
            # Logging
            print('Type/Version error in raw block headers')
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

        # Return dict
        return {
            "prev_id": prev_id,
            "merkle_root": merkle_root,
            "target": target,
            "nonce": nonce,
            "timestamp": timestamp
        }

    def raw_block_transactions(self, raw_txs: str):
        # Type version
        if not self.verify_type_version(self.F.BLOCK_TX_TYPE, self.F.VERSION, raw_txs):
            # Logging
            print('Type/Version error in raw block transactions')
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

    def block_from_dict(self, block_dict: dict):
        # Construct block
        prev_id = block_dict['prev_id']
        merkle_root = block_dict['merkle_root']
        target = self.F.int_from_target(block_dict['target'])
        nonce = block_dict['nonce']
        timestamp = block_dict['timestamp']
        mining_tx_dict = block_dict['mining_tx']
        height = mining_tx_dict['height']
        reward = mining_tx_dict['reward']
        block_fees = mining_tx_dict['block_fees']
        mining_utxo_dict = mining_tx_dict['mining_utxo']
        amount = mining_utxo_dict['amount']
        address = mining_utxo_dict['address']
        block_height = mining_utxo_dict['block_height']
        mining_tx = MiningTransaction(height, reward, block_fees, address, block_height)
        tx_count = block_dict['tx_count']
        transactions = []
        for x in range(tx_count):
            tx_dict = block_dict[f'tx_{x}']
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
            transactions.append(Transaction(inputs, outputs))

        temp_block = Block(prev_id, target, nonce, timestamp, mining_tx, transactions)
        if temp_block.merkle_root == merkle_root:
            return temp_block
        else:
            # Logging
            print('Block failed to reconstruct from dict.')
            return None
