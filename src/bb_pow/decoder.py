'''
Decoder - decodes various formatted data structs
'''
import basicblockchains_ecc.elliptic_curve

from .formatter import Formatter


class Decoder:
    F = Formatter()

    def decode_cpk(self, cpk: str) -> tuple:
        '''
        The cpk is a hex string - this may or may not having leading '0x' indicator.
        Hence we obtain the x point first by moving from EOS backwards, then what's left is parity integer.
        '''
        parity = int(cpk[:-self.F.HASH_CHARS], 16) % 2
        x = int(cpk[-self.F.HASH_CHARS:], 16)

        curve = basicblockchains_ecc.elliptic_curve.secp256k1()

        # Check x
        try:
            assert curve.is_x_on_curve(x)
        except AssertionError:
            # Logging
            print('x not on curve')
            return (None,)

        # Get y
        temp_y = curve.find_y_from_x(x)

        # Check parity
        y = None
        y = temp_y if temp_y % 2 == parity else curve.p - temp_y

        # Check point
        try:
            assert curve.is_point_on_curve((x, y))
        except AssertionError:
            # Logging
            print('Point not on curve')
            return (None,)
        # Return point
        return (x, y)
