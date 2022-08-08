'''
Tests for formatter and decoder
'''

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