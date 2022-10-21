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
    DIR_PATH = 'data/'
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
                 logger=None, local=False):
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
        if local:
            self.ip = self.get_local_ip()
        else:
            self.ip = self.get_ip()
        self.node = (self.ip, self.assigned_port)
        self.dir_path = os.path.join(dir_path, str(self.assigned_port))
        self.db_file = db_file
        self.wallet_file = wallet_file

        # Create Blockchain object
        self.blockchain = Blockchain(self.dir_path, self.db_file, logger=self.logger)

        # Create Block queue for miner
        self.block_queue = Queue()

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
    def start_miner(self):
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
                self.mining_thread = threading.Thread(target=self.mining_monitor)
                self.logger.debug('Starting mining thread.')
                self.mining_thread.start()

            else:
                # Logging
                self.logger.info('Miner already running.')
        else:
            # Logging
            self.logger.warning('Must be connected to network to start miner.')

    def mining_monitor(self):
        self.logger.debug('Mining monitor running')
        while self.is_mining and self.is_connected:
            unmined_block = self.create_next_block()

            # Logging
            self.logger.info(f'Mining block at height {unmined_block.height}')

            # Process
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
                        self.logger.debug('Mining interrupt received.')
                        mining = False
            if next_block:
                added = self.add_block(next_block)
                if added:
                    # Logging
                    self.logger.info(f'Successfully mined block at height {next_block.height}')
                    self.gossip_protocol_block(next_block)
                else:
                    # Logging
                    self.logger.warning(
                        f'Block mined but failed to be added. Likely fork. Current forks: {self.blockchain.forks}')

        self.logger.debug('Mining monitor terminated.')

    def stop_miner(self):
        if self.is_mining:
            # Kill mining process
            if self.mining_process.is_alive():
                self.mining_process.terminate()
            self.is_mining = False

            # Logging
            self.logger.debug('Terminating mining functions')

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

            # Wait until mining thread dies
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

        # Disaster recovery timestamp
        timestamp = utc_to_seconds()
        if timestamp > self.last_block.timestamp + pow(self.f.HEARTBEAT, 2):
            timestamp = self.last_block.timestamp + pow(self.f.HEARTBEAT, 2) - 1

        # Return unmined block
        return Block(self.last_block.id, self.target, 0, timestamp, mining_tx, self.block_transactions)

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
            utxo_dict = self.blockchain.chain_db.get_utxo(tx_id, tx_index)
            if utxo_dict:
                total_input_amount += utxo_dict['amount']
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
    def add_block(self, block: Block, catching_up=False) -> bool:
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

            # Check orphans if not catching up
            if not catching_up:
                # Check if orphaned transactions are now valid
                self.check_for_tx_parents()

                # Check if orphaned blocks are now valid
                self.check_for_block_parents()
        elif block.height > self.height:
            self.orphaned_blocks.append(block)

        return added

    # --- ADD TRANSACTION --- #

    def add_transaction(self, transaction: Transaction) -> bool:
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

            # -- CONSTRUCTION -- #

            # Get UTXO
            utxo_output_dict = self.blockchain.chain_db.get_utxo(tx_id, tx_index)

            if utxo_output_dict == {}:
                self.logger.warning(f'Unable to find utxo with id {tx_id} and index {tx_index}. Orphan transaction.')
                orphan = True

            # Validate the referenced output utxo
            else:
                # Get values
                amount = utxo_output_dict['amount']
                address = utxo_output_dict['address']
                block_height = utxo_output_dict['block_height']
                # amount = amount_dict['amount']
                # address = address_dict['address']
                # block_height = block_height_dict['block_height']

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
            self.gossip_protocol_tx(transaction)

        # Flagged for orphaned. Add to orphan pool
        else:
            self.orphaned_transactions.append(transaction)

        return True

    # --- ORPHANS --- #

    def check_for_tx_parents(self):
        '''
        After a Block is saved, we iterate over all orphaned transactions to see if their parent UTXOs were saved.
        However, when validating a transaction, we check if it's raw_tx is already in the validated_transactions and
        orphaned_transactions pool. Hence, for the Node, when checking for an orphans parents, we make sure the
        transaction itself is removed from the orphaned_transaction pool.
        '''
        orphan_index = self.orphaned_transactions.copy()
        for x in range(0, len(orphan_index)):
            tx = self.orphaned_transactions.pop(0)
            self.add_transaction(tx)

    def check_for_block_parents(self):
        orphan_index = self.orphaned_blocks.copy()
        for x in range(0, len(orphan_index)):
            try:
                block = self.orphaned_blocks.pop(0)
                self.add_block(block)
            except IndexError:
                # Logging
                self.logger.debug(
                    f'Tried to pop block from empty list. Orphan index: {orphan_index}, Orphaned blocks: {self.orphaned_blocks}')

    # --- NETWORK --- #

    def catchup_to_network(self):
        # Get node list - remove own nodes
        temp_nodes = self.node_list.copy()
        if self.node in temp_nodes:
            temp_nodes.remove(self.node)

        # If temp_nodes not empty, try and catchup
        if len(temp_nodes) > 0:
            random_node = random.choice(temp_nodes)
            self.network_height = self.get_height(random_node)
            while self.height < self.network_height:
                # Class variables for gui loading screen
                self.percent_complete = int((self.height / self.network_height) * 100)

                # Get random node
                random_node = random.choice(temp_nodes)

                # Catching up flag
                catching_up = False
                if self.height < self.network_height - 1:
                    catching_up = True

                # Get next raw block
                next_raw_block = self.get_raw_block_from_node(random_node, block_index=self.height + 1)
                if next_raw_block:
                    next_block = self.d.raw_block(next_raw_block)
                    added = self.add_block(next_block, catching_up=catching_up)
                    if added:
                        # Logging
                        self.logger.info(f'Successfully added block at height {self.height} from {random_node}')
                    else:
                        # Logging
                        self.logger.error(f'Unable to add block at height {self.height} from {random_node}')
                        break
                else:
                    # Logging
                    self.logger.error(f'Received NONE from get raw block request from {random_node}')
                    break

                # Update network height when at final HEARTBEAT blocks
                if self.network_height > self.f.HEARTBEAT and (self.network_height - self.height) == self.f.HEARTBEAT:
                    # Logging
                    self.logger.debug(f'Updating network height before retrieving final {self.f.HEARTBEAT} blocks')
                    self.network_height = self.get_height(random_node)

        self.logger.info('Node height equal to network height')

    # --- PUT METHODS --- #
    def connect_to_network(self, node=LEGACY_NODE) -> bool:
        # Check connection first
        if self.is_connected:
            # Logging
            self.logger.info('Already connected to network')
            return False

        # Logging
        self.logger.info(f'Attempting to connect to network through {node}.')

        # Update connected status
        self.is_connected = True

        # Get current node list
        current_nodes = self.node_list.copy()

        # Add own node to node list
        if self.node not in self.node_list:
            self.node_list.append(self.node)

        # Return true if own node
        if node == self.node:
            return True

        # Logging
        self.logger.info('Retrieving node lists. May take a few minutes.')

        # Retrieve formatted node list
        initial_node_list = self.get_node_list(node)
        for init_node in initial_node_list:
            if init_node not in self.node_list:
                self.node_list.append(init_node)

        # Get remaining nodes
        all_nodes = False
        while not all_nodes and current_nodes != []:
            all_nodes = True
            random_node = random.choice(current_nodes)
            another_node_list = self.get_node_list(random_node)
            for check_node in another_node_list:
                if check_node not in self.node_list:
                    all_nodes = False
                    self.node_list.append(check_node)

        # Logging
        self.logger.info('Connecting to nodes in node list. May take a few minutes.')

        # Connect to every node in node list
        for n in self.node_list:
            if n != self.node:
                self.connect_to_node(n)

        # Logging
        self.logger.info('Beginning download of saved blocks. Do not close or exit program.')

        # Catchup to network
        self.catchup_to_network()

        # Get validated txs
        self.get_validated_txs_from_node(node)

        return True

    # --- GET METHODS --- #

    def ping_node(self, node: tuple) -> bool:
        '''
        Ping endpoint for 200 response
        '''
        try:
            r = requests.get(self.make_url(node, 'ping'), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for ping.')
            return False

        return r.status_code == 200

    def check_genesis(self, node: tuple) -> bool:
        '''
        We get the genesis block from the node and compare with ours. Return True if same, False if otherwise
        '''
        # Return true if it's our own node
        if node == self.node:
            return True

        # Get genesis block from node at /genesis_block/ endpoint
        try:
            r = requests.get(self.make_url(node, 'genesis_block'), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.warning(f'Unable to get genesis block from {node}')
            return False

        # Decode
        try:
            raw_genesis = r.json()['raw_genesis']
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.critical(f'Unable to decode raw_genesis dict from {node}')
            return False

        # Verify
        if raw_genesis != self.blockchain.chain[0].raw_block:
            # Logging
            self.logger.critical(f'Raw genesis block retrieved from {node} does not match local raw block.')
            return False

        return True

    def check_connected_status(self, node: tuple) -> bool:
        '''
        Returns true if /is_connected endpoint on node returns 200
        '''
        # Get response from /is_connected/ endpoint
        try:
            r = requests.get(self.make_url(node, 'is_connected'), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.warning(f'Unable to get connection from {node}')
            return False

        # Return True if r.status_code == 200
        return r.status_code == 200

    def check_disconnected_status(self, node: tuple) -> bool:
        '''
        Returns true if node is still active but has disconnected status (used in network disconnection)
        '''
        # Get status
        try:
            r = requests.get(self.make_url(node, 'is_connected'), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.warning(f'Unable to get connection from {node}')
            return False

        # Return True if r.statis_code == 202
        return r.status_code == 202

    def get_height(self, node: tuple) -> int:
        '''
        Get height dict from /height/ endpoint from
        '''
        height = 0
        try:
            r = requests.get(self.make_url(node, 'height'), headers=self.request_header)
            height = r.json()['height']
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Unable to connect to {node} for height')
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.error(f'Unable to decode json response from {node} for height')
        return height

    def get_node_list(self, node: tuple) -> list:
        # Account for calling local node
        if node in [self.node, ('127.0.0.1', self.assigned_port), ('localhost', self.assigned_port)]:
            # Logging
            self.logger.warning('Requesting node_list from self.')
            return []

        # Get request to /node_list/ endpoint
        try:
            r = requests.get(self.make_url(node, 'node_list'), headers=self.request_header)
            node_list = r.json()
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.critical(f'Unable to connect to network through {node}')
            self.is_connected = False
            return []
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.critical(f'Unable to decode node list from {node}')
            self.is_connected = False
            return []

        # Return list of nodes as tuples
        if node_list:
            formatted_node_list = []
            for list_tuple in node_list:
                temp_node = (list_tuple[0], list_tuple[1])
                formatted_node_list.append(temp_node)
            return formatted_node_list
        else:
            # Logging
            self.logger.error(f'Retrieved empty node list from {node}')
            return []

    def get_raw_block_from_node(self, node: tuple, block_index=None):
        raw_block = None
        url = self.make_url(node, 'raw_block')
        if block_index is not None:
            url += str(block_index)
        try:
            r = requests.get(url, headers=self.request_header)
            raw_block_dict = r.json()
            raw_block = raw_block_dict['raw_block']
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Unable to connect to {node} for raw block')
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.error(f'Unable to decode raw_block dict from {node}')
        except ValueError:
            # Logging
            self.logger.error(f'Malformed raw block dict from {node}')
        return raw_block

    def get_validated_txs_from_node(self, node: tuple) -> bool:
        try:
            r = requests.get(self.make_url(node, 'transactions'), headers=self.request_header)
            validated_tx_dict = r.json()
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Error connecting to {node} for validated txs.')
            return False
        except requests.exceptions.JSONDecodeError:
            # Logging
            self.logger.error(f'Error decoding tx dict from {node} for validated txs')
            return False

        tx_num = validated_tx_dict['validated_txs']
        for x in range(tx_num):
            tx_dict = validated_tx_dict[f'valid_tx_{x + 1}']
            tx = self.d.transaction_from_dict(tx_dict)
            tx_added = self.add_transaction(tx)
            if tx_added:
                # Logging
                self.logger.info(f'Successfully validated tx with id {tx.id} obtained from {node}')
            else:
                # Logging
                self.logger.warning(f'Error validating tx with id {tx.id} obtained from {node}')
        return True

    # --- POST METHODS --- #

    def connect_to_node(self, node: tuple) -> bool:
        # Post self.node to node_list endpoint in node api
        data = {'ip': self.ip, 'port': self.assigned_port}
        try:
            r = requests.post(self.make_url(node, 'node'), data=json.dumps(data), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.error(f'Could not connect to {node}')
            return False

        # Success
        if r.status_code == 200:
            # Add node if not in node_list
            if node not in self.node_list:
                self.node_list.append(node)
                # Logging
                self.logger.info(f'Successfully connected to {node}')
            else:
                # Logging
                self.logger.info(f'{node} already in node list')
            return True

        # Already connected
        elif r.status_code == 202:
            # Logging
            self.logger.info(f'Already connected to {node}')
            return True

        # Failure
        else:
            # Logging
            self.logger.error(
                f'Error connecting to {node}.\n Status code: {r.status_code}.\n Response message: {r.content.decode()}.')
            return False

    def send_raw_block_to_node(self, raw_block: str, node: tuple) -> bool:
        '''
        Posting block at /raw_block/ endpoint of node api
        '''
        data = {'raw_block': raw_block}
        try:
            r = requests.post(self.make_url(node, 'raw_block'), data=json.dumps(data), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.warning(f'Unable to send raw block at height {self.d.raw_block(raw_block).height} to {node}')
            return False
        return r.status_code == 200

    def send_raw_tx_to_node(self, raw_tx: str, node: tuple) -> bool:
        '''
        Posting tx at /raw_tx/ endpoint of node api
        '''
        data = {'raw_tx': raw_tx}
        try:
            r = requests.post(self.make_url(node, 'raw_tx'), data=json.dumps(data), headers=self.request_header)
        except requests.exceptions.ConnectionError:
            # Logging
            self.logger.warning(f'Unable to send raw tx with id {self.d.raw_transaction(raw_tx).id} to {node}')
            return False
        return r.status_code == 200

    # --- DELETE METHODS --- #
    def disconnect_from_network(self):
        # Stop all mining
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
            self.logger.error(f'{self.node} already removed from node list.')

        # Copy node list for indexing
        node_index = self.node_list.copy()

        # Self node for disconnect
        data = {'ip': self.ip, 'port': self.assigned_port}
        for node in node_index:
            try:
                r = requests.delete(self.make_url(node, 'node'), data=json.dumps(data),
                                    headers=self.request_header)
                if r.status_code != 200:
                    # Logging
                    self.logger.error(f'Received error code during DELETE request: {r.status_code} from {node}')
                self.node_list.remove(node)
            except requests.exceptions.ConnectionError:
                # Logging
                self.logger.error(f'Error connecting to {node} for disconnect.')
            except ValueError:
                # Logging
                self.logger.warning(f'{node} not found in node_list')

        # Finish with empty node list
        self.node_list = []

        # Logging
        self.logger.info('Disconnected from network.')

    # --- GOSSIP PROTOCOLS --- #

    def gossip_protocol_tx(self, tx: Transaction):
        node_list_index = self.node_list.copy()
        if self.node in node_list_index:
            node_list_index.remove(self.node)
        gossip_count = 0
        while gossip_count < self.f.GOSSIP_NUMBER and node_list_index != []:
            list_length = len(node_list_index)
            gossip_node = node_list_index.pop(secrets.randbelow(list_length))
            # Logging
            self.logger.info(f'Sending tx with id {tx.id} to {gossip_node}')
            status_code = self.send_raw_tx_to_node(tx.raw_tx, gossip_node)
            if status_code == 200:
                # Logging
                self.logger.info(f'Received 200 code from {gossip_node} for tx {tx.id}.')
                gossip_count += 1

    def gossip_protocol_block(self, block: Block):
        node_list_index = self.node_list.copy()
        if self.node in node_list_index:
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

    # --- NETWORKING TOOLS --- #
    def make_url(self, node: tuple, endpoint: str):
        ip, port = node
        return f'http://{ip}:{port}/{endpoint}/'

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

    @staticmethod
    def get_local_ip():
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

    @staticmethod
    def get_ip():
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
