'''
The Block class
'''
from .transactions import Transaction
from hashlib import sha256
import json


class Block():
    '''
    A Block can be instantiated with the following values:
        -previous block id
        -target
        -nonce
        -timestamp (in UNIX seconds from epoch)
        -transaction list

    The Merkle Root for the transaction list will be calculated automatically
    '''

    def __init__(self, prev_id: str, target: int, nonce: int, timestamp: int, transactions: list):
        self.previous_id = prev_id
        self.target = hex(target)  # Keep target as hex string for ease of use
        self.nonce = nonce
        self.timestamp = timestamp
        self.transactions = transactions

        # Calculate merkle root
        self.merkle_root = calc_merkle_root(self.tx_ids)

    def __repr__(self):
        return self.to_json

    @property
    def to_json(self):
        block_dict = {
            "previous_id": self.previous_id,
            "target": self.target,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "tx_count": len(self.transactions)
        }
        for t in self.transactions:
            block_dict.update({
                f'tx_{self.transactions.index(t)}': json.loads(t.to_json)
            })
        return json.dumps(block_dict)

    @property
    def tx_ids(self):
        return [tx.id for tx in self.transactions]

    @property
    def id(self):
        return sha256(self.to_json.encode()).hexdigest()


# --- Merkle Root Calculations ---#

def calc_merkle_root(hash_list: list):
    '''
    Calculate Merkle Root
    1 - Compute the tx_hash of each value in the list
    2 - If list is odd, duplicate the last value
    3 - Concatenate the sequential pairs of hashes
    4 - Repeat 2 and 3 until there is only 1 hash left. This is the merkle root
    '''
    tx_hashes = hash_list
    while len(tx_hashes) != 1:
        tx_hashes = hashpairs(tx_hashes)
    return tx_hashes[0]


def hashlist(list_to_hash: list):
    return [sha256(raw_hex.encode()).hexdigest() for raw_hex in list_to_hash]


def hashpairs(list_to_hash: list):
    if len(list_to_hash) == 1:
        return list_to_hash
    elif len(list_to_hash) % 2 == 1:
        list_to_hash.append(list_to_hash[-1])

    return [sha256((list_to_hash[2 * x] + list_to_hash[2 * x + 1]).encode()).hexdigest() for x in
            range(len(list_to_hash) // 2)]


# --- Merkle Proof ---#
def find_hashpair(tx_id: str, hash_list: list):
    '''

    '''

    if tx_id in hash_list:
        # Return hashlist if it contains the root
        if len(hash_list) == 1:
            return tx_id
        # Balance hashlist otherwise
        elif len(hash_list) % 2 == 1:
            hash_list.append(hash_list[-1])

        index = hash_list.index(tx_id)
        if index % 2 == 0:
            # Pair is on the right
            hash_pair = hash_list[index + 1]
            return hash_pair, False
        else:
            # Pair is on the left
            hash_pair = hash_list[index - 1]
            return hash_pair, True


def merkle_proof(tx_id: str, hash_list: list, merkle_root: str):
    '''

    '''
    tx_hashes = hash_list
    if tx_id in tx_hashes:
        # Find layers of tree
        layers = 0
        while pow(2, layers) < len(tx_hashes):
            layers += 1

        # Construct proof
        proof = []
        temp_id = tx_id
        while len(tx_hashes) != 1:
            hash_pair, is_left = find_hashpair(temp_id, tx_hashes)
            proof.append({layers: hash_pair, 'is_left': is_left})
            if is_left:
                temp_id = sha256((hash_pair + temp_id).encode()).hexdigest()
            else:
                temp_id = sha256((temp_id + hash_pair).encode()).hexdigest()
            tx_hashes = hashpairs(tx_hashes)
            layers -= 1

        root = tx_hashes[0]
        proof.append({layers: root, 'root_verified': root == merkle_root})
        return proof
    else:
        return None
