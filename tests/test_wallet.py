'''
Tests for the Wallet class
'''
import os
from pathlib import Path
import logging

from basicblockchains_ecc.elliptic_curve import secp256k1

from .context import Wallet, Decoder
from .helpers import random_hash, random_signature


def test_save_load_wallet():
    current_path = os.getcwd()
    if '/tests' in current_path:
        dir_path = current_path + '/data/test_wallet/'
    else:
        dir_path = './tests/data/test_wallet/'

    test_logger = logging.getLogger(__name__)
    test_logger.setLevel('CRITICAL')
    test_logger.propagate = False
    test_logger.addHandler(logging.StreamHandler())

    w = Wallet(dir_path=dir_path, logger=test_logger)  # Will automatically save
    w2 = Wallet(dir_path=dir_path, logger=test_logger)  # Will load wallet saved in same dir
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
    tx_id = random_hash()
    signature = random_signature(tx_id)

    # Get parts back
    cpk, ecdsa_tuple = d.decode_signature(signature)

    assert curve.verify_signature(ecdsa_tuple, tx_id, curve.decompress_point(cpk))
