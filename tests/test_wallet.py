'''
Tests for the Wallet class
'''
import random

from src.bb_pow.wallet import Wallet, recover_wallet, int_to_base58, base58_to_int, BASE58_ALPHABET, verify_address
import secrets
import string
from hashlib import sha256
from basicblockchains_ecc.elliptic_curve import secp256k1


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
    random_string = ''
    for x in range(0, secrets.randbelow(100)):
        random_string += random.choice(string.ascii_letters)
    tx_id = sha256(random_string.encode()).hexdigest()

    w = Wallet()
    (hr, hs) = w.sign_transaction(tx_id)
    curve = secp256k1()
    assert curve.verify_signature((int(hr, 16), int(hs, 16)), tx_id, w.public_key)


def test_base58():
    '''
    We test base58 encoding and decoding
    '''
    # Verify int -> base58 -> int
    random_num = secrets.randbits(256)
    assert base58_to_int(int_to_base58(random_num)) == random_num

    # Verify base58 -> int -> base58
    string_length = secrets.randbelow(pow(2, 8))
    random_base58_string = ''
    for x in range(0, string_length):
        random_base58_string += random.choice(BASE58_ALPHABET)
    assert int_to_base58(base58_to_int(random_base58_string)) == random_base58_string


def test_verify_address():
    random_address = Wallet().address
    assert verify_address(random_address)
