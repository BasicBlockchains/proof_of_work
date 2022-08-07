'''
The Signature class - All data types have a class method for formatting

Note: All formatted hex strings DO NOT have the leading '0x'.
'''
from basicblockchains_ecc.elliptic_curve import secp256k1
from .formatter import Formatter
import json


class Signature():
    # --- Curve fixed to be secpk256k1
    CURVE = secp256k1()

    def __init__(self, tx_id: str, private_key: int):
        self.ecdsa_tuple = self.CURVE.generate_signature(private_key, tx_id)
        public_key = self.CURVE.scalar_multiplication(private_key, self.CURVE.generator)
        self.cpk = self.CURVE.compress_point(public_key)

    def __repr__(self):
        return self.to_json

    @property
    def to_json(self):
        (r, s) = self.ecdsa_tuple
        signature_dict = {
            "compressed_public_key": self.cpk,
            "r": hex(r),
            "s": hex(s)
        }

    @property
    def raw(self):
        # We use the __repr__ method to format the signature
        f = Formatter()

        # Type/version
        type = format(f.SIGNATURE_TYPE, f'0{f.TYPE_CHARS}x')
        version = format(f.VERSION, f'0{f.VERSION_CHARS}x')

        # Format signature_tuple
        (r, s) = self.ecdsa_tuple
        h_r = hex(r)[2:]
        h_s = hex(s)[2:]
        r_length = format(len(h_r), f'0{f.LENGTH_CHARS}x')
        s_length = format(len(h_s), f'0{f.LENGTH_CHARS}x')

        # Format cpk
        cpk = self.cpk[2:]
        cpk_length = format(len(cpk), f'0{f.LENGTH_CHARS}x')

        # Signature = cpk_length + cpk + r_length + hex(r) + s_length + hex(s)
        return type + version + cpk_length + cpk + r_length + h_r + s_length + h_s

    @property
    def length(self):
        return len(self.raw)
