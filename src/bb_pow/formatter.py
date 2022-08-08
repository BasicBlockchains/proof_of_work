'''
TESTING
'''
import basicblockchains_ecc.elliptic_curve
from hashlib import sha256, sha1


class Formatter():
    '''

    '''
    # Fixed version to start
    VERSION = 0x01
    ACCEPTED_VERSIONS = [0x01]

    # Mine parameters
    TOTAL_MINING_AMOUNT = pow(2, 64) - 1
    STARTING_TARGET_COEFFICIENT = 0x1fffff
    STARTING_TARGET_EXPONENT = 0x1e
    STARTING_REWARD = 0x00010000
    MINING_DELAY = 0  # TESTING #100
    HEARTBEAT = 5  # TESTING #60

    # Formatting parameters
    TYPE_CHARS = 2
    VERSION_CHARS = 2
    COEFF_CHARS = 2
    HASH_CHARS = 64
    TOTAL_MINE_CHARS = 16
    REWARD_CHARS = 8
    TARGET_COEFFICIENT_CHARS = 6
    TARGET_EXPONENT_CHARS = 2
    NONCE_CHARS = 6
    DELAY_CHARS = 2
    HEARTBEAT_CHARS = 2
    MAX_BIT_CHARS = 8
    BLOCK_TX_CHARS = 4
    INDEX_CHARS = 2
    LENGTH_CHARS = 2
    AMOUNT_CHARS = 16
    ADDRESS_CHARS = 48
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

    # Type parameters
    GENESIS_TX_TYPE = 0xff
    GENESIS_BLOCK_TYPE = 0xfe
    UTXO_INPUT_TYPE = 0x11
    UTXO_OUTPUT_TYPE = 0x12
    MINING_TX_TYPE = 0x21
    USER_TX_TYPE = 0x22
    BLOCK_TYPE = 0x31
    ADDRESS_TYPE = 0x41
    SIGNATURE_TYPE = 0x51
    NODE_CONNECT_TYPE = 0x61
    NETWORK_CONNECT_TYPE = 0x62
    DISCONNECT_TYPE = 0x63
    NEW_TX_TYPE = 0x64
    REQUEST_TX_TYPE = 0x65
    NEW_BLOCK_TYPE = 0x66
    INDEXED_BLOCK_TYPE = 0x67
    STATUS_TYPE = 0x68
    HASH_MATCH_TYPE = 0x69
    NODE_LIST_TYPE = 0x6a
    WALLET_CONNECT_TYPE = 0x71
    GET_UTXO_TYPE = 0x72
    GET_HEIGHT_TYPE = 0x73
    CONFIRM_TX_TYPE = 0x74
    CONFIRM_TYPE = 0x01
    ERROR_TYPE = 0x02
    PING_TYPE = 0x03

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

    def format_int(self, num: int, character_format: int):
        return format(num, f'0{character_format}x')

    def format_hex(self, hex_string: str, character_format: int):
        while len(hex_string) != character_format:
            hex_string = '0' + hex_string
        return hex_string

    def cpk(self, public_key: tuple):
        (x, y) = public_key
        prefix = '0x02' if (y % 2) == 0 else '0x03'
        return prefix + format(x, f'0{self.HASH_CHARS}x')

    def address(self, cpk: str):
        epk = sha1(
            sha256(cpk.encode()).hexdigest().encode()
        ).hexdigest()

        # Verify epk message digest
        while len(epk) != self.ADDRESS_DIGEST:
            epk = '0' + epk

        checksum = sha256(
            sha256(epk.encode()).hexdigest().encode()
        ).hexdigest()[:self.CHECKSUM_CHARS]

        # Prefix type and version
        type = format(self.ADDRESS_TYPE, f'0{self.TYPE_CHARS}x')
        version = format(self.VERSION, f'0{self.VERSION_CHARS}x')

        # Address = type + version + epk + checksum (26 byte address)
        return self.int_to_base58(int(type + version + epk + checksum, 16))

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
