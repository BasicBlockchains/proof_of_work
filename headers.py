'''
Headers class
'''
import json
from hashlib import sha256

from formatter import Formatter


class Header:

    def __init__(self, prev_id: str, merkle_root: str, target: int, nonce: int, timestamp: int):
        self.prev_id = prev_id
        self.target = target
        self.nonce = nonce
        self.timestamp = timestamp
        self.merkle_root = merkle_root

    def __repr__(self):
        return self.to_json

    @property
    def raw_header(self):
        # Setup formatter
        f = Formatter()

        # Type/version
        type = format(f.HEADER_TYPE, f'0{f.TYPE_CHARS}x')
        version = f.VERSION

        # Format headers
        prev_id = f.format_hex(self.prev_id, f.HASH_CHARS)
        merkle_root = f.format_hex(self.merkle_root, f.HASH_CHARS)
        target = f.target_from_int(self.target)
        nonce = format(self.nonce, f'0{f.NONCE_CHARS}x')
        timestamp = format(self.timestamp, f'0{f.TIMESTAMP_CHARS}x')

        # Raw = type + version + prev_hash + merkle_root + target + nonce + timestamp
        return type + version + prev_id + merkle_root + target + nonce + timestamp

    @property
    def to_json(self):
        # Setup formatter
        f = Formatter()

        header_dict = {
            "prev_id": self.prev_id,
            "merkle_root": self.merkle_root,
            "target": f.target_from_int(self.target),
            "nonce": self.nonce,
            "timestamp": self.timestamp
        }
        return json.dumps(header_dict)

    @property
    def id(self):
        return sha256(self.raw_header.encode()).hexdigest()
