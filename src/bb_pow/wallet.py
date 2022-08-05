'''
The Wallet class
'''
import json
import secrets
from hashlib import sha256, sha512, sha1
from pathlib import Path
from basicblockchains_ecc import elliptic_curve as EC
import pandas as pd


class Wallet():
    '''
    The Wallet can be instantiated with a seed value, which will be used to generate the private and public keys of
    the user. If no seed is provided a random one will be generated. We generate a corresponding seed phrase for
    convenience. This seed phrase depends on the dictionary file "english_dictionary.txt", located in the ./data
    folder. As well the Wallet has the ability to save the seed to a wallet.dat file, which will be kept in the
    ./data folder unless otherwise specified. We the use the secp256k1 curve to generate keys, and for the ECDSA. We
    use Python's secrets package to generate cryptographically strong random numbers.
    '''

    # ---Constants
    DICTIONARY_EXPONENT = 11

    def __init__(self, seed=None, seed_bits=128):
        # Use secp256k1 curve as standard
        self.curve = EC.secp256k1()

        # Allow seed_bits to be variable
        self.seed_bits = seed_bits

        # Establish seed
        if not seed:
            seed = self.get_seed()

        # Create seed phrase
        self.seed_phrase = self.get_seed_phrase(seed)

        # Create keys - seed dropped after generating keys
        self.private_key, self.public_key = self.get_keys(seed)
        self.compressed_public_key = self.curve.compress_point(self.public_key)

        # Create address
        self.address = create_address(self.compressed_public_key)

    # --- SEED METHODS --- #

    def get_seed(self):
        seed = 0
        while seed.bit_length() != self.seed_bits:
            seed = secrets.randbits(self.seed_bits)
        return seed

    def get_seed_phrase(self, seed: int):
        '''
        Will generate a seed phrase from a given seed.
        Phrase will be index values in the dictionary.
        Dictionary size is given by 2^DICTIONARY_EXPONENT.
        The bits and seed_checksum bits need to sum to a value divisible by DICTIONARY_EXPONENT
        '''
        # Create binary string with bits size
        entropy = bin(seed)[2:]

        # If entropy != seed_bits for some reason, take the first seed_bit values of the binary hash
        if len(entropy) != self.seed_bits:
            entropy = bin(int(sha256(entropy.encode()).hexdigest(), 16))[2:2 + self.seed_bits]

        # Dynamically find checksum length so that seed_bits + checksum = 0 (mod DICT_EXP)
        # Note that if seed_bits % 11 == 0 already, the checksum_length will be non-zero
        checksum_length = self.DICTIONARY_EXPONENT - (self.seed_bits % self.DICTIONARY_EXPONENT)

        # Get binary checksum value
        checksum = sha256(entropy.encode()).hexdigest()
        binary_checksum = bin(int(checksum, 16))[2:2 + checksum_length]

        # Seed_phrase index string = entropy + binary_checksum
        index_string = entropy + binary_checksum

        # Use the string to determine word indices
        index_list = []
        for x in range(0, len(index_string) // self.DICTIONARY_EXPONENT):
            indice = index_string[x * self.DICTIONARY_EXPONENT: (x + 1) * self.DICTIONARY_EXPONENT]
            index_list.append(int(indice, 2))

        # Load dictionary from file - save seed and return empty list if file not found
        try:
            # dir_path = Path(__file__).parent / "data/english_dictionary.txt"
            df_dict = pd.read_csv('./data/english_dictionary.txt', header=None)
        except FileNotFoundError:
            self.save_seed(seed)
            return []

        # Retrieve the words at the given index and return the seed phrase
        word_list = []
        for i in index_list:
            word_list.append(df_dict.iloc[[i]].values[0][0])
        return word_list

    @staticmethod
    def recover_seed(seed_phrase: list, seed_bits=128, dir_path='./data/', dict_exp=DICTIONARY_EXPONENT):
        # Try to read file
        try:
            df_dict = pd.read_csv(dir_path + 'english_dictionary.txt', header=None)
        except FileNotFoundError:
            # Logging
            return None

        # Get the dictionary index from the word
        number_list = [df_dict.index[df_dict[0] == s].values[0] for s in seed_phrase]

        # Express the index as a binary string of fixed DICT_EXP length
        index_string = ''
        for n in number_list:
            index_string += format(n, f"0{dict_exp}b")

        # Get the first self.bits from the binary string and return the corresponding integer
        return int(index_string[:seed_bits], 2)

    def save_seed(self, seed: int, dir_path="./data/"):
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Write seed to file as hex string
        with open(dir_path + "wallet.dat", "w") as f:
            f.write(hex(seed))

    # --- GENERATE KEYS ---#
    def get_keys(self, seed: int):
        # Take the 512-bit hash of the seed hex string (with leading 0x
        seed_hash512 = sha512(hex(seed).encode()).hexdigest()

        # Private key is the first 256 bits (64 hex chars) of the 512-bit hash
        private_key = int(seed_hash512[:64], 16)

        # Chain code is second 256 bits of the 512-bit hash
        self.chain_code = int(seed_hash512[64:], 16)

        # Public key comes from secp256k1
        public_key = self.curve.scalar_multiplication(private_key, self.curve.generator)

        return private_key, public_key

    # --- SIGN TRANSACTION --- #
    def sign_transaction(self, tx_id: str):
        return self.curve.generate_signature(self.private_key, tx_id)

    def encode_signature(self, signature: tuple):
        '''
        Given a signature tuple (r,s) for a given tx_id, the signature can be verified with the public key.
        Hence to encode the signature, we provide the compressed public key and the values r and s.
        Each value will be written as a hex string WITHOUT the leading '0x'. As these values can vary, they will be preceded by a 1-byte length code.
        Thus the signature will be encoded as:

            compressed_key_length + compressed_key + r_length + r + s_length + s
        '''
        r, s = signature
        h_r = hex(r)[2:]
        h_s = hex(s)[2:]
        r_length = format(len(h_r), '02x')
        s_length = format(len(h_s), '02x')

        cpk = self.compressed_public_key[2:]
        cpk_length = format(len(cpk), '02x')

        return cpk_length + cpk + r_length + h_r + s_length + h_s

    @staticmethod
    def decode_signature(signature: str):
        '''
        We decode and return CPK, (r,s). NOTE: CPK will be a hex string again starting with '0x'
        '''
        # CPK
        cpk_length = int(signature[:2], 16)
        cpk = '0x' + signature[2:2 + cpk_length]

        # R
        r_index = 2 + cpk_length
        r_length = int(signature[r_index:r_index + 2], 16)
        r = int(signature[r_index + 2:r_index + 2 + r_length], 16)

        # S
        s_index = r_index + 2 + r_length
        s_length = int(signature[s_index:s_index + 2], 16)
        s = int(signature[s_index + 2:s_index + 2 + s_length], 16)

        return cpk, (r, s)

    # def decode_signature(self, signature: str):
    #     '''
    #     Given the signature string, we decode and return the signature tuple (r,s)
    #     '''
    #     cpk_length =
    #     # r_length = int(signature[:2], 16)
    #     # r = int(signature[2:2 + r_length], 16)
    #     # s_length = int(signature[2 + r_length:4 + r_length], 16)
    #     # s = int(signature[4 + r_length:4 + r_length + s_length], 16)
    #
    #     #return (r, s)


# --- RECOVER WALLET --- #
def recover_wallet(seed_phrase: list):
    seed = Wallet.recover_seed(seed_phrase)
    return Wallet(seed)


# --- BASE58 ENCODING/DECODING --- #
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BASE58_LIST = [x for x in BASE58_ALPHABET]


def int_to_base58(num: int) -> str:
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
            base58_string = BASE58_LIST[remainder] + base58_string
            num = num // 58
    return base58_string


def base58_to_int(base58_string: str) -> int:
    '''
    To convert a base58 string back to an int:
        -For each character, find the numeric index in the list of alphabet characters
        -Multiply this numeric value by a corresponding power of 58
        -Sum all values
    '''
    return sum([BASE58_LIST.index(base58_string[x:x + 1]) * pow(58, len(base58_string) - x - 1) for x in
                range(0, len(base58_string))])


# --- ADDRESS --- #

def create_address(compressed_public_key: str) -> str:
    '''
    We use the following address algorithm
    1) Take the SHA256 of the compressed_public_key string
    2) Take the SHA1 of the above hash result - ensure it's 40 characters. Call this the encoded public key (EPK)
    3) Take the first 8 characters of SHA256 of the SHA256 of the EPK. This is the checksum
    4) Append the checksum to EPK - call this the checksum encoded public key (CEPK)
    5) Return the base58 encoding of the CEPK.
    '''
    # Get EPK
    epk = sha1(
        sha256(compressed_public_key.encode()).hexdigest().encode()
    ).hexdigest()

    # Make sure it's 40 characters
    while len(epk) != 40:
        epk = '0' + epk

    # Get checksum
    checksum = sha256(
        sha256(epk.encode()).hexdigest().encode()
    ).hexdigest()[:8]

    # Create cepk and return address
    cepk = epk + checksum
    return int_to_base58(int(cepk, 16))


def verify_address(address: str) -> bool:
    '''
    We decode from base58 and verify that the epk generates the expected checksum
    '''
    hex_addy = hex(base58_to_int(address))[2:]
    epk = hex_addy[:-8]
    checksum = hex_addy[-8:]

    # Make sure epk is 40 characters
    while len(epk) != 40:
        epk = '0' + epk

    return sha256(
        sha256(epk.encode()).hexdigest().encode()
    ).hexdigest()[:8] == checksum
