'''
Tests for formatter and decoder
'''
import random
import secrets

from .context import Decoder, Formatter
from .helpers import random_hash, random_public_key, random_address, random_signature, random_target_exponent, \
    random_target_coefficient, random_target

# --- CONSTANTS --- #
f = Formatter()
d = Decoder()


def test_cpk():
    public_key = random_public_key()
    cpk = f.cpk(public_key)
    decoded_cpk = d.decode_cpk(cpk)
    assert public_key == decoded_cpk


def test_base58():
    '''
    We test base58 encoding and decoding
    '''

    # Verify int -> base58 -> int
    random_num = secrets.randbits(256)
    assert f.base58_to_int(f.int_to_base58(random_num)) == random_num

    # Verify base58 -> int -> base58
    string_length = 0
    while string_length < 1:
        string_length = secrets.randbelow(pow(2, 8))
    random_base58_string = ''
    for x in range(0, string_length):
        random_base58_string += random.choice(f.BASE58_ALPHABET)

    # Remove prepended zeros from random_string
    while random_base58_string[:1] == '1':
        random_base58_string = random_base58_string[1:]

    assert f.int_to_base58(f.base58_to_int(random_base58_string)) == random_base58_string


def test_verify_address():
    assert d.verify_address(random_address())


def test_verify_signature():
    tx_id = random_hash()
    signature = random_signature(tx_id)
    assert d.verify_signature(signature, tx_id)


def test_target():
    # Test parts --> target --> parts
    random_coeff = random_target_coefficient()
    random_exp = random_target_exponent()
    target = f.target_from_parts(random_coeff, random_exp)
    decoded_coeff, decoded_exp = f.get_target_parts(target)
    assert decoded_coeff == random_coeff
    assert decoded_exp == random_exp

    # Test target --> parts --> target
    next_target = random_target()
    next_coeff, next_exp = f.get_target_parts(next_target)
    assert f.target_from_parts(next_coeff, next_exp) == next_target
