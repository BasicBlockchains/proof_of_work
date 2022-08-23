'''
The Wallet class
'''
import secrets
from hashlib import sha512
from pathlib import Path

from basicblockchains_ecc import elliptic_curve as EC

from ..data_format.decoder import Decoder
from ..data_format.formatter import Formatter


class Wallet():
    '''
    The Wallet can be instantiated with a seed value, which will be used to generate the private and public keys of
    the user. If no seed is provided a random one will be generated. As well the Wallet has the ability to save the
    seed to a wallet.dat file, which will be kept in the ./data folder unless otherwise specified. We the use the
    secp256k1 curve to generate keys, and for the ECDSA. We use Python's secrets package to generate
    cryptographically strong random numbers.
    '''
    # File constants
    DIR_PATH = './data'
    FILE_NAME = 'wallet.dat'

    # ---Constants
    DICTIONARY_EXPONENT = 11
    F = Formatter()
    D = Decoder()

    def __init__(self, seed=None, seed_bits=128, dir_path=DIR_PATH, file_name=FILE_NAME, save=True):
        # Use secp256k1 curve as standard
        self.curve = EC.secp256k1()

        # Set path and filename variables
        self.dir_path = dir_path
        self.file_name = file_name

        # Allow seed_bits to be variable
        self.seed_bits = seed_bits

        # If file exists, load seed
        if seed is None and Path(self.dir_path, self.file_name).exists():
            seed = self.load_wallet(self.dir_path, self.file_name)

        # If loading returns None, create seed
        if seed is None:
            seed = self.get_seed()

        # Save seed
        if save:
            self.save_wallet(seed, self.dir_path, self.file_name)

        # Create keys - seed dropped after generating keys
        self.private_key, self.public_key = self.get_keys(seed)
        self.compressed_public_key = self.F.cpk(self.public_key)

        # Create address
        self.address = self.F.address(self.compressed_public_key)

    # -- SAVE/LOAD --- #
    def save_wallet(self, seed: int, dir_path: str, file_name: str):
        '''
        We save the necessary values to instantiate a wallet to a file.
        '''
        # Create directory if it doesn't exist
        Path(dir_path).mkdir(parents=True, exist_ok=True)

        with open(f'{dir_path}/{file_name}', 'w') as f:
            seed_string = hex(seed) + '\n'
            f.write(seed_string)

    def load_wallet(self, dir_path: str, file_name: str):
        '''
        We decode the encrypted file and use the values to instantiate the Wallet
        '''
        # Check for file
        file_exists = Path(dir_path, file_name).exists()
        if file_exists:
            # Read in wallet file
            with open(f'{dir_path}/{file_name}', 'r') as f:
                seed_string = f.read()
            if seed_string:
                return int(seed_string, 16)

        # Logging
        return None

    # --- SEED METHODS --- #

    def get_seed(self):
        seed = 0
        while seed.bit_length() != self.seed_bits:
            seed = secrets.randbits(self.seed_bits)
        return seed

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

