'''
The Wallet class
'''
import secrets
from hashlib import sha256, sha512
from pathlib import Path

import pandas as pd
from basicblockchains_ecc import elliptic_curve as EC

from .decoder import Decoder
from .formatter import Formatter


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
    F = Formatter()
    D = Decoder()

    def __init__(self, seed=None, seed_bits=128):
        # Use secp256k1 curve as standard
        self.curve = EC.secp256k1()

        # Allow seed_bits to be variable
        self.seed_bits = seed_bits

        # Establish seed - allow for zero case
        if seed is None:
            seed = self.get_seed()

        # Create seed phrase
        self.seed_phrase = self.get_seed_phrase(seed)

        # Create keys - seed dropped after generating keys
        self.private_key, self.public_key = self.get_keys(seed)
        self.compressed_public_key = self.F.cpk(self.public_key)

        # Create address
        self.address = self.F.address(self.compressed_public_key)

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
    def sign_transaction(self, tx_id: str) -> str:
        return self.F.signature(self.private_key, tx_id)


# --- RECOVER WALLET --- #
def recover_wallet(seed_phrase: list):
    seed = Wallet.recover_seed(seed_phrase)
    return Wallet(seed)
