'''
The Wallet class
'''
import json
import logging
import random
import secrets
from hashlib import sha512
from pathlib import Path

import pandas as pd
import requests
from basicblockchains_ecc import elliptic_curve as EC

from decoder import Decoder
from formatter import Formatter
from transactions import Transaction
from utxo import UTXO_INPUT, UTXO_OUTPUT


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

    # Network constants
    LEGACY_IP = '23.233.30.136'
    LEGACY_PORT = 41000
    LEGACY_NODE = (LEGACY_IP, LEGACY_PORT)

    # UTXO Constants
    COLUMNS = ['tx_id', 'tx_index', 'amount', 'block_height']

    # Constants for requests
    request_header = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    # ---Constants
    F = Formatter()
    D = Decoder()

    def __init__(self, seed=None, seed_bits=128, dir_path=DIR_PATH, file_name=FILE_NAME, save=True, logger=None):
        # Loggging
        if logger:
            self.logger = logger.getChild('Wallet')
        else:
            self.logger = logging.getLogger('Wallet')
            self.logger.setLevel('DEBUG')
            self.logger.addHandler(logging.StreamHandler())

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

        # Logging
        self.logger.debug(f'Logger instantiated in wallet with address{self.address} with name: {self.logger.name}')

        # Create node list
        self.node_list = []

        # Create empty utxo dataframe
        self.utxos = pd.DataFrame(columns=self.COLUMNS)

        # Create list for pending transactions
        self.pending_transactions = []

        # Height var
        self.height = 0

    # --- PROPERTIES --- #
    @property
    def balance(self):
        return self.utxos['amount'].sum()

    @property
    def block_locked(self):
        temp_df = self.utxos.loc[self.utxos['block_height'] > self.height]
        return temp_df['amount'].sum()

    @property
    def spendable(self):
        return (self.balance - self.block_locked)

    @property
    def utxo_list(self):
        return self.utxos.values.tolist()

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
                seed_string = f.read().strip('\n')
            if seed_string:
                return int(seed_string, 16)

        # Logging
        self.logger.warning(f'Wallet file {file_name} not found at {dir_path}')
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

    # --- CREATE TRANSACTION  --- #
    def create_transaction(self, address: str, amount: int, fees=0, block_height=0):
        '''
        We gather the available UTXOs and create an output UTXO with the given address and amount and a return UTXO
        for our own wallet
        '''
        # Verify amount - return None if not enough money
        if amount + fees > self.spendable:
            # Logging
            self.logger.warning('Insufficient funds')
            return None

        # Copy utxos
        utxo_pool = self.utxos.copy()

        # Get latest height
        if len(self.node_list) < 1:
            self.get_node_list()
        self.get_latest_height(random.choice(self.node_list))

        # Remove utxos with incorrect blockheight
        utxo_pool.drop(utxo_pool[utxo_pool['block_height'] > self.height].index, inplace=True)

        utxo_amount = 0
        inputs = []
        row = 0
        while utxo_amount < amount + fees and row < 256:
            utxo_row = utxo_pool.iloc[row].values.tolist()
            tx_id = utxo_row[0]
            output_index = utxo_row[1]
            utxo_amount += utxo_row[2]
            signature = self.sign_transaction(tx_id)
            utxo_input = UTXO_INPUT(tx_id, output_index, signature)
            inputs.append(utxo_input)
            # self.utxos = self.utxos.drop(index=row)
            row += 1

        if row == 256:
            # Logging
            self.logger.error('TX Created with more than 256 Inputs. Rejecting transaction.')
            return None

        utxo_output = UTXO_OUTPUT(amount=amount, address=address, block_height=block_height)
        outputs = [utxo_output]
        rebate = utxo_amount - (amount + fees)
        if rebate > 0:
            utxo_rebate = UTXO_OUTPUT(amount=rebate, address=self.address)
            outputs.append(utxo_rebate)

        new_tx = Transaction(inputs, outputs)
        self.pending_transactions.append(new_tx)

        return new_tx

    # --- NETWORK METHODS --- #

    def post_transaction_to_node(self, tx: Transaction, node=LEGACY_NODE) -> bool:
        ip, port = node
        url = f'http://{ip}:{port}/transaction/'
        data = {'raw_tx': tx.raw_tx}
        r = requests.post(url, data=json.dumps(data), headers=self.request_header)
        if r.status_code in [201, 202]:
            # Logging
            self.logger.info(f'New tx sent to {node}')
            return True
        else:
            # Logging
            self.logger.error(f'Error sending tx to {node}. Status: {r.status_code}')
            return False

    def get_node_list(self, node=LEGACY_NODE) -> bool:
        ip, port = node
        url = f'http://{ip}:{port}/node_list'
        r = requests.get(url, headers=self.request_header)
        list_of_nodes = r.json()

        if list_of_nodes:
            self.node_list = []
            for list_tuple in list_of_nodes:
                new_ip, new_port = list_tuple
                self.node_list.append((new_ip, new_port))
            return True
        else:
            # Logging
            self.logger.warning(f'Unable to get node list from {node}')
            return False

    def get_utxos_from_node(self, node=LEGACY_NODE):
        try:
            temp_ip, temp_port = node
            url = f'http://{temp_ip}:{temp_port}/{self.address}'
            r = requests.get(url, headers=self.request_header)
            utxo_dict = r.json()
            return utxo_dict
        except ConnectionRefusedError:
            # Logging
            self.logger.warning(f'Unable to connect to {node}. Update node list.')
            return {}

    def get_latest_height(self, node=LEGACY_NODE):
        try:
            temp_ip, temp_port = node
            url = f'http://{temp_ip}:{temp_port}/height'
            r = requests.get(url, headers=self.request_header)
            height_dict = r.json()
            self.height = height_dict['height']
        except ConnectionRefusedError:
            # Logging
            self.logger.warning(f'Unable to connect to {node}. Update node list.')
            return {}

    def confirm_tx_by_id(self, tx_id: str) -> bool:
        node = random.choice(self.node_list)
        ip, port = node
        url = f'http://{ip}:{port}/transaction/{tx_id}'
        r = requests.get(url, headers=self.request_header)
        tx_dict = r.json()
        in_chain = tx_dict["in_chain"]
        return in_chain

    # --- UTXO METHODS --- #
    def update_utxo_df(self, utxos: dict):
        temp_df = pd.DataFrame(columns=self.COLUMNS)
        try:
            utxo_count = utxos['utxo_count']
            for x in range(utxo_count):
                utxo_dict = utxos[f'utxo_{x}']
                tx_id = utxo_dict['tx_id']
                tx_index = utxo_dict['tx_index']
                amount = utxo_dict['output']['amount']
                block_height = utxo_dict['output']['block_height']
                utxo_row = pd.DataFrame([[tx_id, tx_index, amount, block_height]], columns=self.COLUMNS)
                temp_df = pd.concat([temp_df, utxo_row], ignore_index=True)
            self.utxos = temp_df
        except KeyError:
            # Logging
            self.logger.error(f'No utxo_count value found in utxo dict: {utxos}')

    def update_utxos_from_pending_transactions(self):

        pending_tx_index = self.pending_transactions.copy()

        for tx in pending_tx_index:
            removed = False
            if self.confirm_tx_by_id(tx.id):
                self.pending_transactions.remove(tx)
                removed = True
            if not removed:
                # Remove referenced inputs
                for utxo_input in tx.inputs:
                    tx_id = utxo_input.tx_id
                    tx_index = utxo_input.index
                    utxo_index = self.utxos.index[
                        (self.utxos['tx_id'] == tx_id) & (self.utxos['tx_index'] == tx_index)]
                    if not utxo_index.empty:
                        self.utxos = self.utxos.drop(index=utxo_index).reset_index(drop=True)
                # Add output utxos if not already added
                for utxo_output in tx.outputs:
                    if utxo_output.address == self.address:
                        new_row = pd.DataFrame(
                            [[tx.id, tx.outputs.index(utxo_output), utxo_output.amount, utxo_output.block_height]],
                            columns=self.COLUMNS)
                        exists_index = self.utxos.index[
                            (self.utxos['tx_id'] == tx.id) & (self.utxos['tx_index'] == tx.outputs.index(utxo_output))
                            ]
                        if exists_index.empty:
                            if self.utxos.empty:
                                self.utxos = new_row
                            else:
                                self.utxos = pd.concat([self.utxos, new_row], ignore_index=True)
