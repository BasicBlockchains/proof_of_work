'''
Tests for the Node class
'''
import os

from .context import Node, Wallet, Block, utc_to_seconds, Transaction, MiningTransaction, Miner, UTXO_INPUT, \
    UTXO_OUTPUT, Formatter


def create_test_node_block(node: Node):
    # Get as many validated transactions that will fit in the Block
    bit_size = 0
    node.block_transactions = []
    while bit_size <= node.f.MAXIMUM_BIT_SIZE and node.validated_transactions != []:
        node.block_transactions.append(node.validated_transactions.pop(0))  # Add first validated transaction
        bit_size += len(node.block_transactions[-1].raw_tx) * 4  # Increase bit_size by number of hex chars * 4

    # Get block fees
    block_fees = 0
    for tx in node.block_transactions:
        block_fees += node.get_fees(tx)

    # Create Mining Transaction
    mining_tx = MiningTransaction(node.height + 1, node.mining_reward, block_fees, node.wallet.address, node.height + 1)

    # Return unmined block
    return Block(node.last_block.id, node.target, 0, utc_to_seconds(), mining_tx, node.block_transactions)


def test_add_transaction():
    # Create db with path in tests directory
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_node/'
    else:
        dir_path = './tests/data/test_node/'
    file_name = 'test_add_transaction.db'

    # Formatter
    f = Formatter()

    # Create Node
    n = Node(dir_path, file_name)

    # Set connected flag
    n.is_connected = True

    # CHANGE MINING DELAY
    n.blockchain.f.MINING_DELAY = 0

    # CHANGE blockchain target
    n.blockchain.target = f.target_from_parts(f.STARTING_TARGET_COEFFICIENT, 0x1f)

    # Mine necessary Block
    block1 = create_test_node_block(n)
    m = Miner()
    mined_block1 = m.mine_block(block1)
    m.is_mining = False
    assert n.add_block(mined_block1, gossip=False)

    # UTXO_INPUT
    tx_id = n.last_block.mining_tx.id
    tx_index = 0
    signature = n.wallet.sign_transaction(tx_id)
    utxo_input = UTXO_INPUT(tx_id, tx_index, signature)

    # UTXO_OUTPUTS
    amount = n.mining_reward // 2
    new_address = Wallet().address
    utxo_output1 = UTXO_OUTPUT(amount=amount, address=new_address)
    utxo_output2 = UTXO_OUTPUT(amount=amount, address=n.wallet.address)

    # Transaction
    new_tx = Transaction(inputs=[utxo_input], outputs=[utxo_output1, utxo_output2])

    # Create Orphan transaction
    orphan_id = new_tx.id
    orphan_output_index = new_tx.outputs.index(utxo_output2)
    orphan_sig = n.wallet.sign_transaction(orphan_id)
    orphan_utxo_input = UTXO_INPUT(orphan_id, orphan_output_index, orphan_sig)

    orphan_utxo_output1 = UTXO_OUTPUT(amount=amount // 2, address=new_address)
    orphan_utxo_output2 = UTXO_OUTPUT(amount=amount // 2, address=n.wallet.address)

    orphan_tx = Transaction(inputs=[orphan_utxo_input], outputs=[orphan_utxo_output1, orphan_utxo_output2])

    # Add Transactions
    assert n.add_transaction(new_tx, gossip=False)
    assert n.add_transaction(orphan_tx, gossip=False)
    assert n.validated_transactions[0].raw_tx == new_tx.raw_tx
    assert n.orphaned_transactions[0].raw_tx == orphan_tx.raw_tx

    # Mine next Block
    block2 = n.create_next_block()
    mined_block2 = m.mine_block(block2)
    m.is_mining = False
    assert n.add_block(mined_block2, gossip=False)

    # Check tx got mined and orphan is validated
    assert n.orphaned_transactions == []
    assert n.validated_transactions[0].raw_tx == orphan_tx.raw_tx
    assert n.blockchain.find_block_by_tx_id(new_tx.id).raw_block == n.last_block.raw_block

    # Empty blocks for next time
    while n.height > 0:
        n.blockchain.pop_block()
