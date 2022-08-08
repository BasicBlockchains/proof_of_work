'''
Decoder - decodes various formatted data structs
'''
from basicblockchains_ecc.elliptic_curve import secp256k1

from .formatter import Formatter
from hashlib import sha256
import json
from .utxo import UTXO_INPUT, UTXO_OUTPUT


class Decoder:
    F = Formatter()
    t_index = F.TYPE_CHARS
    v_index = t_index + F.VERSION_CHARS

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

        # Verify type/version
        type = int(signature[:self.F.TYPE_CHARS], 16)
        version = int(signature[self.F.TYPE_CHARS:self.F.TYPE_CHARS + self.F.VERSION_CHARS], 16)

        try:
            assert type == self.F.SIGNATURE_TYPE
            assert version in self.F.ACCEPTED_VERSIONS
        except AssertionError:
            # Logging
            print('Signature has incorrect type and/or version')
            return False

        # Indexing
        start_index = self.F.TYPE_CHARS + self.F.VERSION_CHARS
        cpk_index = start_index + self.F.COEFF_CHARS + self.F.HASH_CHARS
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

        while len(epk) != self.F.ADDRESS_DIGEST:
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

    def raw_utxo_input(self, raw_utxo: str):
        # Type and version
        type = int(raw_utxo[:self.t_index], 16)
        version = int(raw_utxo[self.t_index:self.v_index], 16)

        try:
            assert type == self.F.UTXO_INPUT_TYPE
            assert version in self.F.ACCEPTED_VERSIONS
        except AssertionError:
            # Logging
            print('Type/version error when decoding raw utxo input')
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
        # Type and version
        type = int(raw_utxo[:self.t_index], 16)
        version = int(raw_utxo[self.t_index:self.v_index], 16)

        try:
            assert type == self.F.UTXO_OUTPUT_TYPE
            assert version in self.F.ACCEPTED_VERSIONS
        except AssertionError:
            # Logging
            print('Type/version error when decoding raw utxo output')
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
