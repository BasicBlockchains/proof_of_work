'''
Tests for the Wallet class
'''
import random
import secrets
import string
from hashlib import sha256

from basicblockchains_ecc.elliptic_curve import secp256k1

from src.bb_pow.components.wallet import Wallet, recover_wallet
from src.bb_pow.data_format.decoder import Decoder


def test_seed_recover():
    '''
    We verify that the seed_phrase recovers the same seed
    '''
    w = Wallet()
    recovered_seed = w.recover_seed(w.seed_phrase)
    w2 = Wallet(recovered_seed)
    assert w.seed_phrase == w2.seed_phrase


def test_wallet_recovery():
    w = Wallet()
    calc_wallet = recover_wallet(w.seed_phrase)
    assert w.seed_phrase == calc_wallet.seed_phrase


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
