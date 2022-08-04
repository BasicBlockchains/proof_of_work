'''
Tests for the Wallet class
'''
from src.bb_pow.wallet import Wallet


def test_seed_recover():
    '''
    We verify that the seed_phrase recovers the same seed
    '''
    w = Wallet()
    recovered_seed = w.recover_seed(w.seed_phrase)
    w2 = Wallet(recovered_seed)
    assert w.seed_phrase == w2.seed_phrase
