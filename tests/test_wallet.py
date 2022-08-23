'''
Tests for the Wallet class
'''
import random
import secrets
import string
from hashlib import sha256
import os
from basicblockchains_ecc.elliptic_curve import secp256k1
from pathlib import Path

from src.bb_pow.components.wallet import Wallet
from src.bb_pow.data_format.decoder import Decoder


def test_save_load_wallet():
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_wallet/'
    else:
        dir_path = './tests/data/test_wallet/'

    w = Wallet(dir_path=dir_path)  # Will automatically save
    w2 = Wallet(dir_path=dir_path)  # Will load wallet saved in same dir
    assert w.private_key == w2.private_key

    # Delete wallets
    wallet_file = os.path.join(dir_path, 'wallet.dat')
    os.remove(wallet_file)

    # Verify
    assert not Path(wallet_file).exists()


def test_wallet_signature():
    # Setup: decoder and curve
    d = Decoder()
    curve = secp256k1()

    # Generate transaction
    tx_id = random_tx_id()
    w = Wallet()
    signature = w.sign_transaction(tx_id)

    # Get parts back
    cpk, ecdsa_tuple = d.decode_signature(signature)

    assert curve.verify_signature(ecdsa_tuple, tx_id, curve.decompress_point(cpk))


# --- HELPER METHODS --- #
def random_tx_id():
    random_string = ''
    for x in range(0, secrets.randbelow(100)):
        random_string += random.choice(string.ascii_letters)
    return sha256(random_string.encode()).hexdigest()
