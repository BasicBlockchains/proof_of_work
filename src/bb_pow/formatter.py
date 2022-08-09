'''
TESTING
'''
import basicblockchains_ecc.elliptic_curve
from hashlib import sha256, sha1


class Formatter():
    # TYPE/VERSION
    TYPE_CHARS = 2
    VERSION_CHARS = 2
<<<<<<< HEAD
=======
    COEFF_CHARS = 2
    HASH_CHARS = 64
    TOTAL_MINE_CHARS = 16
    REWARD_CHARS = 8
    TARGET_COEFFICIENT_CHARS = 6
    TARGET_EXPONENT_CHARS = 2
    NONCE_CHARS = 8
    DELAY_CHARS = 2
    HEARTBEAT_CHARS = 2
    MAX_BIT_CHARS = 8
    BLOCK_TX_CHARS = 4
    INDEX_CHARS = 2
    LENGTH_CHARS = 2
    AMOUNT_CHARS = 16
    ADDRESS_DIGEST = 40
    CHECKSUM_CHARS = 8
    HEIGHT_CHARS = 16
    COUNT_CHARS = 2
    IP_CHARS = 8
    PORT_CHARS = 4
    TIMEOUT_CHARS = 2
    RETRY_CHARS = 2
    DATA_LENGTH_CHARS = 8
    TIMESTAMP_CHARS = 8

    TARGET_CHARS = TARGET_COEFFICIENT_CHARS + TARGET_EXPONENT_CHARS
    SIGNATURE_CHARS = TYPE_CHARS + VERSION_CHARS + COEFF_CHARS + 3 * HASH_CHARS
    ADDRESS_CHARS = TYPE_CHARS + VERSION_CHARS + ADDRESS_DIGEST + CHECKSUM_CHARS
    HEADERS_CHARS = TYPE_CHARS + VERSION_CHARS + 2 * HASH_CHARS + TARGET_CHARS + NONCE_CHARS + TIMESTAMP_CHARS

    # Type parameters
    GENESIS_TX_TYPE = 0xff
    GENESIS_BLOCK_TYPE = 0xfe
    UTXO_INPUT_TYPE = 0x11
    UTXO_OUTPUT_TYPE = 0x12
    TX_TYPE = 0x21
    MINING_TX_TYPE = 0x22
    BLOCK_TYPE = 0x31
    BLOCK_HEADER_TYPE = 0x32
    BLOCK_TX_TYPE = 0x33
    ADDRESS_TYPE = 0x41
    SIGNATURE_TYPE = 0x51
>>>>>>> mining_tx

    # Fixed version to start
    VERSION = 0x01
    ACCEPTED_VERSIONS = [0x01]
    FORMATTED_VERSION = format(VERSION, f'0{VERSION_CHARS}x')

    # Assigned Types
    UTXO_INPUT_TYPE = 0x11
    UTXO_OUTPUT_TYPE = 0x12
    TX_TYPE = 0x21
    MINING_TX_TYPE = 0x22
    BLOCK_TYPE = 0x31
    BLOCK_HEADER_TYPE = 0x32
    BLOCK_TX_TYPE = 0x33
    ADDRESS_TYPE = 0x41
    SIGNATURE_TYPE = 0x51

    # CRYPTORGRAPHIC FORMATTING
    # Cpk and signature
    HASH_CHARS = 64
    PREFIX_CHARS = 2
    CPK_CHARS = PREFIX_CHARS + HASH_CHARS
    SIGNATURE_CHARS = TYPE_CHARS + VERSION_CHARS + CPK_CHARS + (2 * HASH_CHARS)

    # Address
    EPK_CHARS = 40
    CHECKSUM_CHARS = 8
    ADDRESS_CHARS = TYPE_CHARS + VERSION_CHARS + EPK_CHARS + CHECKSUM_CHARS

    # UTXO FORMATTING
    # Input
    TX_ID_CHARS = 64
    INDEX_CHARS = 2

    # Output
    AMOUNT_CHARS = 16
    HEIGHT_CHARS = 16

    # TRANSACTION FORMATTING
    COUNT_CHARS = 2

    # # Mine parameters
    # TOTAL_MINING_AMOUNT = pow(2, 64) - 1
    # STARTING_TARGET_COEFFICIENT = 0x1fffff
    # STARTING_TARGET_EXPONENT = 0x1e
    # STARTING_REWARD = 0x00010000
    # MINING_DELAY = 0  # TESTING #100
    # HEARTBEAT = 5  # TESTING #60
    #
    # # Formatting parameters
    # TYPE_CHARS = 2
    # VERSION_CHARS = 2
    # COEFF_CHARS = 2
    # HASH_CHARS = 64
    # TOTAL_MINE_CHARS = 16
    # REWARD_CHARS = 8
    # TARGET_COEFFICIENT_CHARS = 6
    # TARGET_EXPONENT_CHARS = 2
    # NONCE_CHARS = 8
    # DELAY_CHARS = 2
    # HEARTBEAT_CHARS = 2
    # MAX_BIT_CHARS = 8
    # BLOCK_TX_CHARS = 4
    # INDEX_CHARS = 2
    # LENGTH_CHARS = 2
    # AMOUNT_CHARS = 16
    # ADDRESS_DIGEST = 40
    # CHECKSUM_CHARS = 8
    # HEIGHT_CHARS = 16
    # COUNT_CHARS = 2
    # IP_CHARS = 8
    # PORT_CHARS = 4
    # TIMEOUT_CHARS = 2
    # RETRY_CHARS = 2
    # DATA_LENGTH_CHARS = 8
    # TIMESTAMP_CHARS = 8
    #
    # TARGET_CHARS = TARGET_COEFFICIENT_CHARS + TARGET_EXPONENT_CHARS
    # SIGNATURE_CHARS = TYPE_CHARS + VERSION_CHARS + COEFF_CHARS + 3 * HASH_CHARS
    # ADDRESS_CHARS = TYPE_CHARS + VERSION_CHARS + ADDRESS_DIGEST + CHECKSUM_CHARS
    # HEADERS_CHARS = TYPE_CHARS + VERSION_CHARS + 2 * HASH_CHARS + TARGET_CHARS + NONCE_CHARS + TIMESTAMP_CHARS
    #
    # # Type parameters
    # GENESIS_TX_TYPE = 0xff
    # GENESIS_BLOCK_TYPE = 0xfe

    #

    #
    # --- BASE58 ENCODING/DECODING --- #
    BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    BASE58_LIST = [x for x in BASE58_ALPHABET]

    def int_to_base58(self, num: int) -> str:
        '''
        We create the string by successively dividing by 58 and appending the corresponding symbol to our string.
        '''
        # Start with empty string
        base58_string = ''

        # Return empty string if integer is negative
        if num < 0:
            return base58_string

        # Catch zero case
        if num == 0:
            base58_string = '1'

        # Create string from successive residues
        else:
            while num > 0:
                remainder = num % 58
                base58_string = self.BASE58_LIST[remainder] + base58_string
                num = num // 58
        return base58_string

    def base58_to_int(self, base58_string: str) -> int:
        '''
        To convert a base58 string back to an int:
            -For each character, find the numeric index in the list of alphabet characters
            -Multiply this numeric value by a corresponding power of 58
            -Sum all values
        '''
        return sum([self.BASE58_LIST.index(base58_string[x:x + 1]) * pow(58, len(base58_string) - x - 1) for x in
                    range(0, len(base58_string))])

    ##CPk, Address, Signature

    def cpk(self, public_key: tuple):
        (x, y) = public_key
        prefix = '0x02' if (y % 2) == 0 else '0x03'
        return prefix + format(x, f'0{self.HASH_CHARS}x')

    def address(self, cpk: str):
        epk = sha1(
            sha256(cpk.encode()).hexdigest().encode()
        ).hexdigest()

        # Verify epk message digest
        while len(epk) != self.EPK_CHARS:
            epk = '0' + epk

        checksum = sha256(
            sha256(epk.encode()).hexdigest().encode()
        ).hexdigest()[:self.CHECKSUM_CHARS]

        # Prefix type and version
        type = format(self.ADDRESS_TYPE, f'0{self.TYPE_CHARS}x')
        version = format(self.VERSION, f'0{self.VERSION_CHARS}x')

        # Address = type + version + epk + checksum (26 byte address)
        return self.int_to_base58(int(type + version + epk + checksum, 16))

    def hex_address(self, address: str):
        temp_hex = hex(self.base58_to_int(address))[2:]
        if len(temp_hex) == self.ADDRESS_CHARS:
            return temp_hex
        else:
            t = temp_hex[:self.TYPE_CHARS]
            v = temp_hex[self.TYPE_CHARS:self.TYPE_CHARS + self.VERSION_CHARS]
            s_index = self.TYPE_CHARS + self.VERSION_CHARS
            epk = temp_hex[s_index: -self.CHECKSUM_CHARS]
            checksum = temp_hex[-self.CHECKSUM_CHARS:]
            while len(epk) != self.EPK_CHARS:
                epk = '0' + epk
            return t + v + epk + checksum

    def signature(self, private_key: int, tx_id: str):
        # Get curve
        curve = basicblockchains_ecc.elliptic_curve.secp256k1()

        # Format ecdsa tuple
        (r, s) = curve.generate_signature(private_key, tx_id)
        h_r = format(r, f'0{self.HASH_CHARS}x')
        h_s = format(s, f'0{self.HASH_CHARS}x')

        # Get formatted cpk - remove leading '0x'
        cpk = self.cpk(curve.scalar_multiplication(private_key, curve.generator))[2:]

        # signature = type + version + cpk + h_r + h_s (100 bytes)
        type = format(self.SIGNATURE_TYPE, f'0{self.TYPE_CHARS}x')
        version = format(self.VERSION, f'0{self.VERSION_CHARS}x')

        return type + version + cpk + h_r + h_s
<<<<<<< HEAD
    #
    # # Target
    # def get_target_parts(self, target: int):
    #     '''
    #     We return the corresponding coefficient and exponent parts of the integer target
    #     '''
    #     # Get max power of 2 dividing target
    #     max_power = 0
    #     while target % pow(2, max_power) == 0:
    #         max_power += 1
    #     max_power -= 1
    #
    #     # Get largest multiple of 8 strictly less than max_power
    #     temp_val = max_power - (max_power % 8)
    #
    #     # Get the exponent
    #     E = (temp_val // 8) + 3
    #
    #     # Get the coefficient
    #     c = target // pow(2, 8 * (E - 3))
    #
    #     return c, E
    #
    # def target_from_int(self, target_num: int):
    #     c, E = self.get_target_parts(target_num)
    #     h_coeff = format(c, f'0{self.TARGET_COEFFICIENT_CHARS}x')
    #     h_exp = format(E, f'0{self.TARGET_EXPONENT_CHARS}x')
    #
    #     return h_coeff + h_exp
    #
    # def target_from_parts(self, coeff: int, exp: int):
    #     return coeff * pow(2, 8 * (exp - 3))
    #
    # # UTXOS
    # def utxo_input(self, tx_id: str, index: int, signature: str):
    #     type = format(self.UTXO_INPUT_TYPE, f'0{self.TYPE_CHARS}x')
    #
    #     f_tx_id = self.format_hex(tx_id, self.HASH_CHARS)
    #     f_index = self.format_int(index, self.INDEX_CHARS)
    #
    #     # Raw utxo = type (2 hex) + version (2 hex) + tx_id (64 hex) + index (2 hex) + signature(99 hex) =~ 85 bytes
    #     return type + self.FORMATTED_VERSION + f_tx_id + f_index + signature
    #
    # def utxo_output(self, amount: int, address: str, block_height: int):
    #     type = format(self.UTXO_OUTPUT_TYPE, f'0{self.TYPE_CHARS}x')
    #
    #     f_amount = self.format_int(amount, self.AMOUNT_CHARS)
    #     f_address = self.hex_address(address)
    #     f_block_height = self.format_int(block_height, self.HEIGHT_CHARS)
    #
    #     # Raw utxo = type (2 hex) + version (2 hex) + amount (16 hex) + address (52 hex) + block_height (16 hex) = 44 bytes
    #     return type + self.FORMATTED_VERSION + f_amount + f_address + f_block_height
    #
    # # Transaction
    # def transaction(self, inputs: list, outputs: list):
    #     # Type
    #     type = format(self.TX_TYPE, f'0{self.TYPE_CHARS}x')
    #
    #     # Format input/output counts
    #     input_count = format(len(inputs), f'0{self.COUNT_CHARS}x')
    #     output_count = format(len(outputs), f'0{self.COUNT_CHARS}x')
    #
    #     # Format inputs
    #     input_string = ''
    #     for utxo_input in inputs:
    #         input_string += utxo_input.raw_utxo
    #
    #     # Format outputs
    #     output_string = ''
    #     for utxo_output in outputs:
    #         output_string += utxo_output.raw_utxo
    #
    #     # Raw = type + version + input_count + input_string + output_count + output_string
    #     return type + self.FORMATTED_VERSION + input_count + input_string + output_count + output_string
    #
    # # Block
    # def block(self, prev_id: str, merkle_root: str, target: int, nonce: int, timestamp: int, transactions: list):
    #     # Type
    #     type = format(self.BLOCK_TYPE, f'0{self.TYPE_CHARS}x')
    #
    #     # Headers
    #     headers = self.block_headers(prev_id, merkle_root, target, nonce, timestamp)
    #
    #     # Txs
    #     txs = self.block_transactions(transactions)
    #
    #     # Raw = type + version + headers + txs
    #     return type + self.FORMATTED_VERSION + headers + txs
    #
    # def block_headers(self, prev_id: str, merkle_root: str, target_num: int, nonce: int, timestamp: int):
    #     # Type
    #     type = format(self.BLOCK_HEADER_TYPE, f'0{self.TYPE_CHARS}x')
    #
    #     # Headers
    #     h_prev_id = self.format_hex(prev_id, self.HASH_CHARS)
    #     h_merkle_root = self.format_hex(merkle_root, self.HASH_CHARS)
    #     h_target = self.target_from_int(target_num)
    #     h_nonce = self.format_int(nonce, self.NONCE_CHARS)
    #     h_timestamp = self.format_int(timestamp, self.TIMESTAMP_CHARS)
    #
    #     # Raw = type + version (2 bytes) + prev_id + merkle_root (64 bytes) + target + nonce + timestamp (12 bytes) = 78 bytes
    #     return type + self.FORMATTED_VERSION + h_prev_id + h_merkle_root + h_target + h_nonce + h_timestamp
    #
    # def block_transactions(self, transactions: list):
    #     # Type
    #     type = format(self.BLOCK_TX_TYPE, f'0{self.TYPE_CHARS}x')
    #
    #     # Count
    #     tx_count = format(len(transactions), f'0{self.COUNT_CHARS}x')
    #
    #     # tx_string
    #     tx_string = ''
    #     for tx in transactions:
    #         tx_string += tx.raw_tx
    #
    #     # Raw = type + version (2 bytes) + tx_count (1 byte) + raw_txs (var)
    #     return type + self.FORMATTED_VERSION + tx_count + tx_string
=======

    # Target
    def get_target_parts(self, target: int):
        '''
        We return the corresponding coefficient and exponent parts of the integer target
        '''
        # Get max power of 2 dividing target
        max_power = 0
        while target % pow(2, max_power) == 0:
            max_power += 1
        max_power -= 1

        # Get largest multiple of 8 strictly less than max_power
        temp_val = max_power - (max_power % 8)

        # Get the exponent
        E = (temp_val // 8) + 3

        # Get the coefficient
        c = target // pow(2, 8 * (E - 3))

        return c, E

    def target_from_int(self, target_num: int):
        c, E = self.get_target_parts(target_num)
        h_coeff = format(c, f'0{self.TARGET_COEFFICIENT_CHARS}x')
        h_exp = format(E, f'0{self.TARGET_EXPONENT_CHARS}x')

        return h_coeff + h_exp

    def target_from_parts(self, coeff: int, exp: int):
        return coeff * pow(2, 8 * (exp - 3))

    # UTXOS
    def utxo_input(self, tx_id: str, index: int, signature: str):
        type = format(self.UTXO_INPUT_TYPE, f'0{self.TYPE_CHARS}x')

        f_tx_id = self.format_hex(tx_id, self.HASH_CHARS)
        f_index = self.format_int(index, self.INDEX_CHARS)

        # Raw utxo = type (2 hex) + version (2 hex) + tx_id (64 hex) + index (2 hex) + signature(99 hex) =~ 85 bytes
        return type + self.FORMATTED_VERSION + f_tx_id + f_index + signature

    def utxo_output(self, amount: int, address: str, block_height: int):
        type = format(self.UTXO_OUTPUT_TYPE, f'0{self.TYPE_CHARS}x')

        f_amount = self.format_int(amount, self.AMOUNT_CHARS)
        f_address = self.hex_address(address)
        f_block_height = self.format_int(block_height, self.HEIGHT_CHARS)

        # Raw utxo = type (2 hex) + version (2 hex) + amount (16 hex) + address (52 hex) + block_height (16 hex) = 44 bytes
        return type + self.FORMATTED_VERSION + f_amount + f_address + f_block_height

    # Transactions
    def transaction(self, inputs: list, outputs: list):
        # Type
        type = format(self.TX_TYPE, f'0{self.TYPE_CHARS}x')

        # Format input/output counts
        input_count = format(len(inputs), f'0{self.COUNT_CHARS}x')
        output_count = format(len(outputs), f'0{self.COUNT_CHARS}x')

        # Format inputs
        input_string = ''
        for utxo_input in inputs:
            input_string += utxo_input.raw_utxo

        # Format outputs
        output_string = ''
        for utxo_output in outputs:
            output_string += utxo_output.raw_utxo

        # Raw = type + version + input_count + input_string + output_count + output_string
        return type + self.FORMATTED_VERSION + input_count + input_string + output_count + output_string

    def mining_tx(self, height: int, reward: int, block_fees: int, address: str):
        # Type
        type = format(self.MINING_TX_TYPE, f'0{self.TYPE_CHARS}x')

        # Mining info
        h_height = format(height, f'0{self.HEIGHT_CHARS}x')
        h_reward = format(reward, f'0{self.REWARD_CHARS}x')
        h_fees = format(block_fees, f'0{self.AMOUNT_CHARS}x')
        h_address = self.hex_address(address)

        # Raw = type + version + height + reward + fees + address
        return type + self.FORMATTED_VERSION + h_height + h_reward + h_fees + h_address

    # Block
    def block(self, prev_id: str, merkle_root: str, target: int, nonce: int, timestamp: int, transactions: list):
        # Type
        type = format(self.BLOCK_TYPE, f'0{self.TYPE_CHARS}x')

        # Headers
        headers = self.block_headers(prev_id, merkle_root, target, nonce, timestamp)

        # Txs
        txs = self.block_transactions(transactions)

        # Raw = type + version + headers + txs
        return type + self.FORMATTED_VERSION + headers + txs

    def block_headers(self, prev_id: str, merkle_root: str, target_num: int, nonce: int, timestamp: int):
        # Type
        type = format(self.BLOCK_HEADER_TYPE, f'0{self.TYPE_CHARS}x')

        # Headers
        h_prev_id = self.format_hex(prev_id, self.HASH_CHARS)
        h_merkle_root = self.format_hex(merkle_root, self.HASH_CHARS)
        h_target = self.target_from_int(target_num)
        h_nonce = self.format_int(nonce, self.NONCE_CHARS)
        h_timestamp = self.format_int(timestamp, self.TIMESTAMP_CHARS)

        # Raw = type + version (2 bytes) + prev_id + merkle_root (64 bytes) + target + nonce + timestamp (12 bytes) = 78 bytes
        return type + self.FORMATTED_VERSION + h_prev_id + h_merkle_root + h_target + h_nonce + h_timestamp

    def block_transactions(self, transactions: list):
        # Type
        type = format(self.BLOCK_TX_TYPE, f'0{self.TYPE_CHARS}x')

        # Count
        tx_count = format(len(transactions), f'0{self.COUNT_CHARS}x')

        # tx_string
        tx_string = ''
        for tx in transactions:
            tx_string += tx.raw_tx

        # Raw = type + version (2 bytes) + tx_count (1 byte) + raw_txs (var)
        return type + self.FORMATTED_VERSION + tx_count + tx_string
>>>>>>> mining_tx
