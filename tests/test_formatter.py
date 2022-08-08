'''
Tests for formatter and decoder
'''
import random
import secrets
from src.bb_pow.wallet import Wallet
from src.bb_pow.decoder import Decoder
from src.bb_pow.formatter import Formatter


def test_cpk():
    w = Wallet()
    f = Formatter()
    d = Decoder()

    cpk = f.cpk(w.public_key)
    pk = d.decode_cpk(cpk)
    assert pk == w.public_key


def test_base58():
    '''
    We test base58 encoding and decoding
    '''
    # Formatter
    f = Formatter()

    # Verify int -> base58 -> int
    random_num = secrets.randbits(256)
    assert f.base58_to_int(f.int_to_base58(random_num)) == random_num

    # Verify base58 -> int -> base58
    string_length = secrets.randbelow(pow(2, 8))
    random_base58_string = ''
    for x in range(0, string_length):
        random_base58_string += random.choice(f.BASE58_ALPHABET)

    # Remove prepended zeros from random_string
    while random_base58_string[:1] == '1':
        random_base58_string = random_base58_string[1:]

    assert f.int_to_base58(f.base58_to_int(random_base58_string)) == random_base58_string


def test_verify_address():
    # Decoder
    d = Decoder()
    assert d.verify_address(Wallet().address)
