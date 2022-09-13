'''
The Node class
'''

import json
import logging
import os
import random
import secrets
import socket
import threading
from multiprocessing import Process, Queue

import requests
from requests import get

from block import Block
from blockchain import Blockchain
from decoder import Decoder
from formatter import Formatter
from miner import mine_a_block
from timestamp import utc_to_seconds
from transactions import Transaction, MiningTransaction
from wallet import Wallet


class Node:
    # Directory defaults
    DIR_PATH = './data/'
    DB_FILE = 'chain.db'
    WALLET_FILE = 'wallet.dat'

    # Decoder and formatter
    d = Decoder()
    f = Formatter()

    # Timeout for running processes
    MINER_TIMEOUT = 1
    SERVER_TIMEOUT = 10

    # Port data for flask sever
    LEGACY_IP = '23.233.30.136'
    DEFAULT_PORT = 41000
    LEGACY_NODE = (LEGACY_IP, DEFAULT_PORT)
    PORT_RANGE = 1000

    # Constants for requests
    request_header = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    def __init__(self, dir_path=DIR_PATH, db_file=DB_FILE, wallet_file=WALLET_FILE, port=DEFAULT_PORT, seed=None,
                 logger=None):
        # Loggging
        if logger:
            self.logger = logger.getChild('Node')
        else:
            self.logger = logging.getLogger('Node')
            self.logger.setLevel('DEBUG')
            self.logger.addHandler(logging.StreamHandler())
        self.logger.debug(f'Logger instantiated in Node with name: {self.logger.name}')

        # Set path and filename variables
        self.assigned_port = self.find_open_port(port)
        self.ip = self.get_ip()
        self.node = (self.ip, self.assigned_port)
        self.dir_path = os.path.join(dir_path, str(self.assigned_port))
        self.db_file = db_file
        self.wallet_file = wallet_file

        # Create Blockchain object
        self.blockchain = Blockchain(self.dir_path, self.db_file, logger=self.logger)

        # Create Block queue for miner
        self.block_queue = Queue()

        # Create Miner object
        #self.miner = Miner()

        # Create mining flag for monitoring
        self.is_mining = False

        # Create Wallet object
        self.wallet = Wallet(seed, dir_path=self.dir_path, file_name=self.wallet_file, logger=self.logger)

        # Create transaction lists
        self.validated_transactions = []
        self.orphaned_transactions = []
        self.block_transactions = []

        # Create utxo consumption list
        self.consumed_utxos = []

        # Create orphaned block list
        self.orphaned_blocks = []

        # Create Node list
        self.node_list = []

        # Create connected flag for network
        self.is_connected = False

        # Create network variables for gui
        self.percent_complete = 0
        self.network_height = 0

    # --- PROPERTIES --- #
    @property
    def last_block(self):
        return self.blockchain.last_block

    @property
    def height(self):
        return self.blockchain.height

    @property
    def target(self):
        return self.blockchain.target

    @property
    def mining_reward(self):
        return self.blockchain.mining_reward

    @property
    def total_mining_amount(self):
        return self.blockchain.total_mining_amount

    # --- MINER --- #
    def start_miner(self, gossip=True):
        '''
        Turn on mining thread
        set is_mining to True
        Mining conducted from the monitor
        Must be connected to network in order to mine
        '''
        # Check for network connection
        if self.is_connected:
            if not self.is_mining:
                self.is_mining = True
                self.mining_thread = threading.Thread(target=self.mining_monitor, args=(gossip,))
                self.logger.info('Starting mining thread.')
                self.mining_thread.start()

            else:
                # Logging
                self.logger.info('Miner already running.')
        else:
            # Logging
            self.logger.warning('Must be connected to network to start miner.')

    def mining_monitor(self, gossip: bool):
        self.logger.info('Mining monitor running')
        while self.is_mining and self.is_connected:
            unmined_block = self.create_next_block()

            # Logging
            self.logger.info(f'Mining block at height {unmined_block.height}')

            #Process
            # self.mining_process = Process(target=self.mine_block, args=(unmined_block,))
            # self.mining_process.start()  # Mining happens in its own process

            self.mining_process = Process(target=mine_a_block, args=(unmined_block, self.block_queue))
            self.mining_process.start()

            # Handle blocking function
            next_block = None
            mining = True
            while mining:
                try:
                    next_block = self.block_queue.get(timeout=self.MINER_TIMEOUT)  # Next block is waiting in the thread
                    mining = False
                except Exception:
                    # If not mining, end monitor
                    if not self.is_mining:
                        self.logger.info('Mining interrupt received.')
                        mining = False
            if next_block:
                added = self.add_block(next_block, gossip)
                if added:
                    # Logging
                    self.logger.info(f'Successfully mined block at height {next_block.height}')
                    if gossip:
                        self.gossip_protocol_raw_block(next_block)
                else:
                    # Logging
                    self.logger.warning(
                        f'Block mined but failed to be added. Likely fork. Current forks: {self.blockchain.forks}')

        self.logger.info('Mining monitor terminated.')

    # def mine_block(self, unmined_block: Block):
    #     mined_block = self.miner.mine_block(unmined_block)
    #     self.block_queue.put(mined_block)

    def stop_miner(self):
        if self.is_mining:
            #Kill mining process
            if self.mining_process.is_alive():
                self.mining_process.terminate()
            self.is_mining = False

            #Logging
            self.logger.info('Terminating mining functions')

            # Put block transactions back in validated txs
            block_tx_index = self.block_transactions.copy()
            self.block_transactions = []
            for tx in block_tx_index:
                in_chain = tx.id in self.last_block.tx_ids
                if not in_chain:
                    # Add back consumed utxos
                    for input in tx.inputs:
                        input_tuple = (input.tx_id, input.index)
                        if input_tuple in self.consumed_utxos:
                            self.consumed_utxos.remove(input_tuple)
                    # Revalidate tx
                    self.add_transaction(tx)

            #Wait until mining thread dies
            while self.mining_thread.is_alive():
                pass

    def create_next_block(self):
        # Get as many validated transactions that will fit in the Block
        bit_size = 0
        self.block_transactions = []
        while bit_size <= self.f.MAXIMUM_BIT_SIZE and self.validated_transactions != []:
            self.block_transactions.append(self.validated_transactions.pop(0))  # Add first validated transaction
            bit_size += len(self.block_transactions[-1].raw_tx) * 4  # Increase bit_size by number of hex chars * 4

        # Get block fees
        block_fees = 0
        for tx in self.block_transactions:
            block_fees += self.get_fees(tx)

        # Create Mining Transaction
        mining_tx = MiningTransaction(self.height + 1, self.mining_reward, block_fees, self.wallet.address,
                                      self.height + 1 + self.f.MINING_DELAY)

        # Return unmined block
        return Block(self.last_block.id, self.target, 0, utc_to_seconds(), mining_tx, self.block_transactions)

    def get_fees(self, tx: Transaction):
        '''
        We sum up all input amounts and subtract total output amount
        '''
        total_input_amount = 0
        total_output_amount = 0

        # Iterate over all inputs
        for utxo_input in tx.inputs:
            tx_id = utxo_input.tx_id
            tx_index = utxo_input.index
            utxo_exists = self.blockchain.chain_db.get_utxo(tx_id, tx_index)
            if utxo_exists:
                total_input_amount += utxo_exists['output']['amount']
            # If utxo has been consumed, look for it in the chain
            else:
                temp_tx = self.blockchain.get_tx_by_id(tx_id)
                if temp_tx:
                    total_input_amount += temp_tx.outputs[tx_index].amount
                else:
                    # Logging
                    self.logger.error(
                        f'Unable to find referenced utxo in chain or utxo pool. tx_id: {tx_id}, index: {tx_index}')

        # Iterate over all outputs
        for utxo_output in tx.outputs:
            total_output_amount += utxo_output.amount

        # Fees = total_input_amount - total_output_amount
        return max(0, total_input_amount - total_output_amount)

    # --- ADD BLOCK --- #
    def add_block(self, block: Block, gossip=True) -> bool:
        added = self.blockchain.add_block(block)
        if added:
            # Logging
            self.logger.info(f'Added block at height {block.height}')

            # Remove validated transactions
            validated_tx_index = self.validated_transactions.copy()
            for tx in validated_tx_index:
                if tx.id in self.last_block.tx_ids:
                    self.validated_transactions.remove(tx)
                    # Remove consumed utxos
                    for input in tx.inputs:
                        input_tuple = (input.tx_id, input.index)
                        if input_tuple in self.consumed_utxos:
                            self.consumed_utxos.remove(input_tuple)

            # Check if orphaned transactions are now valid
            self.check_for_tx_parents(gossip)

            # Check if orphaned blocks are now valid
            self.check_for_block_parents()
        elif block.height > self.height:
            self.orphaned_blocks.append(block)
        return added

    # --- ADD TRANSACTION --- #

    def add_transaction(self, transaction: Transaction, gossip=True) -> bool:
        # Make sure tx is not in chain
        existing_tx = self.blockchain.get_tx_by_id(transaction.id)
        if existing_tx:
            # Logging
            self.logger.warning('Transaction already in chain.')
            return False

        # Iterate over validated transactions to make sure transaction not there
        for vt in self.validated_transactions:
            if vt.raw_tx == transaction.raw_tx:
                # Logging
                self.logger.warning('Transaction already in validated tx pools.')
                return False

        # Make sure orphaned transaction was removed from orphaned_transactions list
        for ot in self.orphaned_transactions:
            if ot.raw_tx == transaction.raw_tx:
                # Logging
                self.logger.warning('Transaction already in orphaned tx pools.')
                return False

        # Set orphaned transaction Flag
        orphan = False

        # Validate inputs
        total_input_amount = 0
        for i in transaction.inputs:  # Looping over utxo_input objects

            # Get the row index for the output utxo
            tx_id = i.tx_id
            tx_index = i.index

            # Get values from db
            amount_dict = self.blockchain.chain_db.get_amount_by_utxo(tx_id, tx_index)
            address_dict = self.blockchain.chain_db.get_address_by_utxo(tx_id, tx_index)
            block_height_dict = self.blockchain.chain_db.get_block_height_by_utxo(tx_id, tx_index)

            # If values are empty lists mark for orphan
            if amount_dict == {} or address_dict == {} or block_height_dict == {}:
                # Logging
                self.logger.warning(f'Unable to find utxo with id {tx_id} and index {tx_index}. Orphan transaction.')
                orphan = True

            # Validate the referenced output utxo
            else:
                # Get values
                amount = amount_dict['amount']
                address = address_dict['address']
                block_height = block_height_dict['block_height']

                # Validate the block_height
                if block_height > self.height:
                    # Logging
                    self.logger.error(f'Block height error. UTXO not available until block {block_height}')
                    return False

                # Validate the address from compressed public key
                cpk, (r, s) = self.d.decode_signature(i.signature)
                if not self.f.address(cpk) == address:
                    # Logging
                    self.logger.error(f'CPK/Address error. Address: {address}, CPK Address: {self.f.address(cpk)}')
                    return False

                # Validate the signature
                if not self.d.verify_signature(i.signature, tx_id):
                    # Logging
                    self.logger.error('Signature error')
                    return False

                # Check input not already scheduled for consumption
                input_tuple = (tx_id, tx_index)
                if input_tuple not in self.consumed_utxos:
                    self.consumed_utxos.append(input_tuple)
                else:
                    # Logging
                    self.logger.error('Utxo already consumed by this node')
                    return False

                # Increase total_input_amount
                total_input_amount += amount

        # If not flagged for orphaned
        if not orphan:
            # Get the total output amount
            total_output_amount = 0
            for t in transaction.outputs:
                total_output_amount += t.amount

            # Verify the total output amount
            if total_output_amount > total_input_amount:
                # Logging
                self.logger.error('Input/Output amount error in tx')
                # Unconsume the input tuple in consumed
                for i in transaction.inputs:
                    tx_tuple = (i.tx_id, i.output_index)
                    if tx_tuple in self.consumed_utxos:
                        self.consumed_utxos.remove(tx_tuple)
                return False

            # Add tx to validated tx pool
            self.validated_transactions.append(transaction)

            # Send tx to network
            if gossip:
                self.gossip_protocol_tx(transaction)

        # Flagged for orphaned. Add to orphan pool
        else:
            self.orphaned_transactions.append(transaction)

        return True

    # --- ORPHANS --- #

    def check_for_tx_parents(self, gossip=True):
        '''
        After a Block is saved, we iterate over all orphaned transactions to see if their parent UTXOs were saved.
        However, when validating a transaction, we check if it's raw_tx is already in the validated_transactions and
        orphaned_transactions pool. Hence, for the Node, when checking for an orphans parents, we make sure the
        transaction itself is removed from the orphaned_transaction pool.
        '''
        orphan_index = self.orphaned_transactions.copy()
        for x in range(0, len(orphan_index)):
            tx = self.orphaned_transactions.pop(0)
            self.add_transaction(tx, gossip)

    def check_for_block_parents(self, gossip=True):
        orphan_index = self.orphaned_blocks.copy()
        for x in range(0, len(orphan_index)):
            block = self.orphaned_blocks.pop(0)
            self.add_block(block, gossip)

    # --- NETWORK --- #
    def ping_node(self, node: tuple) -> bool:
        '''
        Ping endpoint for 200 response
        '''
        ip, port = node
        url = f'http://{ip}:{port}/ping'
        try:
            r = requests.get(url, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for ping.')
            return False

        return r.status_code == 200

    def connect_to_node(self, node: tuple) -> bool:
        ip, port = node
        url = f'http://{ip}:{port}/node_list'
        data = {'ip': self.ip, 'port': self.assigned_port}
        try:
            r = requests.post(url, data=json.dumps(data), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            #Logging
            self.logger.error(f'Could not connect to {node}')
            return False
        if r.status_code == 200 and node not in self.node_list:
            correct_genesis = self.check_genesis(node)
            if correct_genesis:
                self.node_list.append(node)
                self.logger.info(f'Successfully connected to {node}')
                return True
            else:
                # Logging
                self.logger.critical(f'Genesis Block malformed in {node}. Not adding to node list.')
                return False
        elif r.status_code == 200:
            # Logging
            self.logger.warning(f'Already connected to {node}')
            return True
        # Logging
        self.logger.error(f'Error connecting to {node}. Status code: {r.status_code}')
        return False

    def connect_to_network(self, node=LEGACY_NODE):
        # Logging
        self.logger.info(f'Connecting to network through {node}')

        # Start with empty list_of_nodes
        list_of_nodes = None

        # Append node to node list
        self.node_list.append(self.node)

        # Get node list from LEGACY_NODE
        ip, port = node
        url = f'http://{ip}:{port}/node_list'
        try:
            r = requests.get(url, headers=self.request_header)
            list_of_nodes = r.json()
        except requests.exceptions.ConnectionError:
            # Logging
            if node == self.LEGACY_NODE:
                self.logger.critical('Unable to connect to legacy node. Manual connection necessary.')
            else:
                self.logger.error(f'Unable to connect to network through {node}.')

        # If we get a node list, we've successfully connected
        if list_of_nodes:
            self.is_connected = True

        # If connected
        if self.is_connected:
            # Connect to each node in node_list
            for list_tuple in list_of_nodes:
                ip, port = list_tuple
                if (ip, port) != self.node:
                    connected = self.connect_to_node((ip, port))
                    if connected:
                        # Logging
                        self.logger.info(f'Successfully connected to {(ip, port)}')
                    else:
                        # Logging
                        self.logger.warning(f'Error connecting to {(ip, port)}')

            # Catchup to network
            self.catchup_to_network()

            # Get validated txs
            gossip_nodes = self.get_gossip_nodes()
            for g_node in gossip_nodes:
                self.request_validated_txs(g_node)
        else:
            self.node_list = []

    def disconnect_from_network(self):
        #Stop all mining
        if self.is_mining:
            self.stop_miner()
            while self.mining_thread.is_alive():
                pass

        # No longer connected - will be used to confirm delete
        self.is_connected = False

        # Remove own node first
        try:
            self.node_list.remove(self.node)
        except ValueError:
            # Logging
            self.logger.warning(f'{self.node} already removed from node list.')

        # Connect to remaining nodes and delete address
        node_index = self.node_list.copy()
        for node in node_index:
            ip, port = node
            url = f'http://{ip}:{port}/node_list'
            data = {'ip': self.ip, 'port': self.assigned_port}
            try:
                r = requests.delete(url, data=json.dumps(data), headers=self.request_header)
                if r.status_code != 200:
                    # Logging
                    self.logger.error(
                        f'Did not receive 200 code from {node} for disconnect. Status code: {r.status_code}')
            except requests.exceptions.ConnectionError:
                #Logging
                self.logger.error(f'Error connecting to {node} for disconnect.')

            self.node_list.remove(node)

    def catchup_to_network(self):
        #Get node list
        node_list_index = self.node_list.copy()

        # Remove own node
        if node_list_index:
            node_list_index.remove(self.node)

        #Iterate over nodes
        if node_list_index != []:
            #Get random node
            random_node = random.choice(node_list_index)
            # Network height class var for use in gui
            self.network_height = self.request_height(random_node)

            while self.height < self.network_height:
                # Class variables for gui loading screen
                self.percent_complete = int((self.height / self.network_height) * 100)

                # Get random node and add next block
                random_node = random.choice(node_list_index)
                next_block = self.request_indexed_raw_block(self.height + 1, random_node)
                added = self.add_block(next_block)
                if added:
                    # Logging
                    self.logger.info(f'Successfully added block at height {self.height} from node {random_node}.')

                else:
                    # Logging
                    self.logger.critical(f'Failed to add block at {self.height + 1} from node {random_node}.')
            self.logger.info('Node height equal to network height')

    def request_height(self, node: tuple) -> int:
        ip, port = node
        url = f'http://{ip}:{port}/height'
        try:
            r = requests.get(url, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for height.')
            return 0
        return r.json()['height']

    def request_validated_txs(self, node: tuple):
        ip, port = node
        url = f'http://{ip}:{port}/transaction'
        try:
            r = requests.get(url, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for validated txs.')
            return
        validated_tx_dict = r.json()
        tx_num = validated_tx_dict['validated_txs']
        for x in range(tx_num):
            tx_dict = validated_tx_dict[f'tx_{x}']
            tx = self.d.transaction_from_dict(tx_dict)
            tx_added = self.add_transaction(tx, gossip=False)
            if tx_added:
                # Logging
                self.logger.info(f'Successfully validated tx with id {tx.id} obtained from {node}')
            else:
                # Logging
                self.logger.error(f'Error validating tx with id {tx.id} obtained from {node}')

    def check_genesis(self, node: tuple) -> bool:
        '''
        We get the genesis block from the node and compare with ours. Return True if same, False if otherwise
        '''
        ip, port = node
        url = f'http://{ip}:{port}/raw_block/0'
        try:
            r = requests.get(url, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            #Logging
            self.logger.critical(f'Unable to get genesis block from {node}')
            return False
        if r.status_code == 200:
            try:
                raw_genesis = r.json()['raw_block']
                if raw_genesis == self.blockchain.chain[0].raw_block:
                    return True
                else:
                    return False
            except KeyError:
                return False
        else:
            # Logging
            self.logger.error(f'Received status code {r.status_code} from  {node}')
            return False

    def send_tx_to_node(self, new_tx: Transaction, node: tuple) -> int:
        ip, port = node
        url = f'http://{ip}:{port}/transaction'
        data = {'raw_tx': new_tx.raw_tx}
        try:
            r = requests.post(url, data=json.dumps(data), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            #Logging
            self.logger.warning(f'Unable to send tx with id {new_tx.id} to {node}')
            return 0
        return r.status_code

    def send_block_to_node(self, block: Block, node: tuple) -> int:
        ip, port = node
        url = f'http://{ip}:{port}/block'
        try:
            r = requests.post(url, data=json.dumps(block.to_json), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            #Logging
            self.logger.warning(f'Unable to send block at height {block.height} to {node}')
            return 0
        return r.status_code

    def send_raw_block_to_node(self, raw_block: str, node: tuple) -> int:
        ip, port = node
        url = f'http://{ip}:{port}/raw_block'
        try:
            r = requests.post(url, data=raw_block, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            #Logging
            self.logger.warning(f'Unable to send raw block at height {self.d.raw_block(raw_block).height} to {node}')
            return 0
        return r.status_code

    def request_indexed_block(self, block_index: int, node: tuple):
        ip, port = node
        url = f'http://{ip}:{port}/block/{block_index}'
        try:
            r = requests.get(url, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for indexed block.')
            return None

        try:
            block_dict = r.json()
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.critical(f'Unable to decode request for index {block_index} from {node}')
            return None

        return self.d.block_from_dict(block_dict)

    def request_indexed_raw_block(self, block_index: int, node: tuple):
        ip, port = node
        url = f'http://{ip}:{port}/raw_block/{block_index}'
        try:
            r = requests.get(url, headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for indexed block.')
            return None

        try:
            block_dict = r.json()
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.critical(f'Unable to decode request for index {block_index} from {node}')
            return None

        return self.d.raw_block(block_dict['raw_block'])

    # --- GOSSIP PROTOCOLS --- #

    def gossip_protocol_tx(self, tx: Transaction):
        node_list_index = self.node_list.copy()
        if node_list_index:
            node_list_index.remove(self.node)
        gossip_count = 0
        while gossip_count < self.f.GOSSIP_NUMBER and node_list_index != []:
            list_length = len(node_list_index)
            gossip_node = node_list_index.pop(secrets.randbelow(list_length))
            # Logging
            self.logger.info(f'Sending tx with id {tx.id} to {gossip_node}')
            status_code = self.send_tx_to_node(tx, gossip_node)
            if status_code == 200:
                # Logging
                self.logger.info(f'Received 200 code from {gossip_node} for tx {tx.id}.')
                gossip_count += 1

    def gossip_protocol_block(self, block: Block):
        node_list_index = self.node_list.copy()
        if node_list_index:
            node_list_index.remove(self.node)
        gossip_count = 0
        while gossip_count < self.f.GOSSIP_NUMBER and node_list_index != []:
            list_length = len(node_list_index)
            gossip_node = node_list_index.pop(secrets.randbelow(list_length))
            # Logging
            self.logger.info(f'Sending block with id {block.id} to {gossip_node}')
            status_code = self.send_block_to_node(block, gossip_node)
            if status_code == 200:
                # Logging
                self.logger.info(f'Received 200 code from {gossip_node} for block {block.id}')
                gossip_count += 1

    def gossip_protocol_raw_block(self, block: Block):
        node_list_index = self.node_list.copy()
        if node_list_index:
            node_list_index.remove(self.node)
        gossip_count = 0
        while gossip_count < self.f.GOSSIP_NUMBER and node_list_index != []:
            list_length = len(node_list_index)
            gossip_node = node_list_index.pop(secrets.randbelow(list_length))
            # Logging
            self.logger.info(f'Sending raw block with id {block.id} to {gossip_node}')
            status_code = self.send_raw_block_to_node(block.raw_block, gossip_node)
            if status_code == 200:
                self.logger.info(f'Received 200 code from {gossip_node} for block {block.id}')
                gossip_count += 1

    def get_gossip_nodes(self):
        # Get gossip nodes
        node_list_index = self.node_list.copy()
        if node_list_index:
            node_list_index.remove(self.node)
        gossip_list = []
        while len(gossip_list) < self.f.GOSSIP_NUMBER and node_list_index != []:
            random_node = random.choice(node_list_index)
            gossip_list.append(random_node)
            node_list_index.remove(random_node)
        return gossip_list

    # --- NETWORKING TOOLS --- #
    def find_open_port(self, desired_port=DEFAULT_PORT):
        port_found = False
        temp_port = desired_port
        while not port_found and temp_port <= self.DEFAULT_PORT + self.PORT_RANGE:
            try:
                temp_socket = self.create_socket()
                temp_socket.bind((socket.gethostname(), temp_port))
                port_found = True
            except OSError:
                # Logging
                self.logger.warning(f'Port {temp_port} occupied.')
                temp_port += 1
        if not port_found:
            return 0
        return temp_port

    def get_local_ip(self):
        '''
        Returns local ip address
        '''
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    def get_ip(self):
        ip = get('https://api.ipify.org').content.decode()
        return ip

    def close_socket(self, socket_toclose: socket):
        socket_toclose.shutdown(socket.SHUT_RDWR)
        socket_toclose.close()

    def create_socket(self):
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        new_socket.settimeout(self.SERVER_TIMEOUT)
        return new_socket



