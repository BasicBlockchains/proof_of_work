'''
TESTING
'''
import basicblockchains_ecc.elliptic_curve
from hashlib import sha256, sha1


class Formatter():
    # TYPE/VERSION
    TYPE_CHARS = 2
    VERSION_CHARS = 2
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
    REWARD_CHARS = 10

    # BLOCK FORMATTING
    NONCE_CHARS = 16
    TIMESTAMP_CHARS = 8
    BLOCK_TX_CHARS = 2
    TARGET_EXPONENT_CHARS = 2
    TARGET_COEFF_CHARS = 6
    TARGET_CHARS = TARGET_COEFF_CHARS + TARGET_EXPONENT_CHARS
    HEADER_CHARS = TYPE_CHARS + VERSION_CHARS + 2 * HASH_CHARS + TARGET_CHARS + NONCE_CHARS + TIMESTAMP_CHARS

    # BLOCKCHAIN FORMATTING
    TOTAL_MINING_AMOUNT = pow(2, 64) - 1
    STARTING_TARGET_COEFFICIENT = 0x1fffff
    STARTING_TARGET_EXPONENT = 0x1e
    STARTING_REWARD = pow(2, 10) * pow(10, 9)  # 1,024,000,000,000
    REWARD_REDUCTION = 0x80520  # 525,600
    MINIMUM_REWARD = pow(10, 9)
    MINING_DELAY = 0  # TESTING #100
    HEARTBEAT = 5  # TESTING #60

    # Ease of use formatting
    def format_hex(self, hex_string: str, hex_length: int):
        if hex_string:
            while len(hex_string) != hex_length:
                hex_string = '0' + hex_string
            return hex_string
        else:
            return format(0, f'0{hex_length}x')

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
        h_coeff = format(c, f'0{self.TARGET_COEFF_CHARS}x')
        h_exp = format(E, f'0{self.TARGET_EXPONENT_CHARS}x')

        return h_coeff + h_exp

    def target_from_parts(self, coeff: int, exp: int):
        return coeff * pow(2, 8 * (exp - 3))

    def int_from_target(self, target: str):
        coeff = int(target[:self.TARGET_COEFF_CHARS], 16)
        exp = int(target[self.TARGET_COEFF_CHARS:], 16)

        return self.target_from_parts(coeff, exp)

    def adjust_target_up(self, num_target: int, adjust_amount: int):
        # Get target parts
        coefficient, exponent = self.get_target_parts(num_target)

        # Verify adding adjust amount doesn't exceed exponent threshold
        if coefficient + adjust_amount >= pow(2, 24):
            exponent += 1
            coefficient = coefficient + adjust_amount - pow(2, 24)
        else:
            coefficient += adjust_amount

        # Not divisible by 8
        if coefficient % 8 == 0:
            coefficient += 1

        return self.target_from_parts(coefficient, exponent)

    def adjust_target_down(self, num_target: int, adjust_amount: int):
        # Get target parts and increase coefficient by 1
        coefficient, exponent = self.get_target_parts(num_target)

        # Verify subtracting exponent doesn't go below 0
        if coefficient - adjust_amount <= 0:
            exponent -= 1
            coefficient = pow(2, 24) + coefficient - adjust_amount

        else:
            coefficient -= adjust_amount

        # Not divisible by 8
        if coefficient % 8 == 0:
            coefficient -= 1

        return self.target_from_parts(coefficient, exponent)
