# An Object Oriented proof of work Blockchain

---

## Encryption

We use ellipitic curve encryption (ECC) with the NIST secp256k1 curve values for the ECDSA signature. These methods are detailed in our ECC package: https://pypi.org/project/basicblockchains-ecc/.


## Wallet
The Wallet class contains the private and public keys used in the ECC. Each wallet can be represented by a seed value, which will be a randomly generated 256-bit integer.
This will be saved as a hex string in plaintext to the user's harddrive. 


### Address and BASE58 Encoding

The create_address algorithm is as follows:

    -Take the SHA1 of the SHA256 of the compressed public key (with leading 0x in the hex string). This yields the encoded public key (EPK)
    -We ensure that the EPK is 40 characters - WILL NOT CONTAIN A LEADING "0x"
    -We take the first 8 characters of the SHA256 of the SHA256 of the EPK. This is the checksum
    -We append the checksum to the EPK to create the checksum encoded public key (CEPK). THIS IS A HEX STRING OF 48 CHARACTERS WITHOUT THE LEADING "0x"
    -The address is the BASE58 encoding of the 48-character CEPK hex string

## UTXOs

## Transactions

## Block

### Merkle root

## Blockchain

### Database

We use SQLite3 as our database. This has a type limitation as their integers are signed and only store (-2^63+1,
2^63-1). Thus all integers saved to the db will be given as hex strings with a prepended '0x'.

I would like to thank Jurko Gospodnetic of stackoverflow for his db query design.
-https://stackoverflow.com/questions/9561832/what-if-i-dont-close-the-database-connection-in-python-sqlite