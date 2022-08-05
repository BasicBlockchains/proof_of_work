# An Object Oriented proof of work Blockchain

---

## Wallet

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