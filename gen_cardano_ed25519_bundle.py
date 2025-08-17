#!/usr/bin/env python3
import json, base64, binascii
from pathlib import Path

from nacl.signing import SigningKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization, hashes
from bech32 import bech32_encode, convertbits
from hashlib import blake2b

# Cardano (addresses)
from pycardano import Address, Network, VerificationKey, StakeVerificationKey, StakeCredential, VerificationKeyHash

OUT = Path("generated/keys")  # output directory

def to_hex(b: bytes) -> str:
    return binascii.hexlify(b).decode()

def bech32_hrp_payload(hrp: str, payload: bytes) -> str:
    words = convertbits(payload, 8, 5, True)
    return bech32_encode(hrp, words)

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # 1) Generate seed + keys (NaCl)
    sk = SigningKey.generate()            # Ed25519
    seed32 = bytes(sk._seed)              # 32B seed
    pub32  = bytes(sk.verify_key)         # 32B public
    
    # Use the same key for both payment and stake
    stake_seed32 = seed32                 # Same seed for staking
    stake_pub32 = pub32                   # Same public key for staking

    # 2) PKCS#8 (DER/PEM) — standard RFC 8410 (działa w WebCrypto i dla PIV import)
    ck = Ed25519PrivateKey.from_private_bytes(seed32)
    pkcs8_der = ck.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pkcs8_pem = ck.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pkcs8_b64 = base64.b64encode(pkcs8_der).decode()

    # Generate public key PEM
    pub_pem = ck.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # 3) OpenSSH (opcjonalnie wygodne do testów)
    openssh_pub = ck.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    ).decode()
    openssh_priv = ck.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption()
    )

    # 4) Cardano keyhash + addresses
    #    keyhash = blake2b-224(pub), enterprise addresses (without stake)
    keyhash = blake2b(pub32, digest_size=28).digest()  # 28B
    
    # Generate proper Cardano addresses with stake keys
    # Create payment verification key
    payment_vkey = VerificationKey.from_primitive(pub32)
    payment_hash = payment_vkey.hash()
    
    # Create stake verification key (using same key)
    stake_vkey = StakeVerificationKey.from_primitive(stake_pub32)
    stake_hash = stake_vkey.hash()
    
    # Create base addresses (payment + stake)
    addr_test = Address(
        payment_part=payment_hash,
        staking_part=stake_hash,
        network=Network.TESTNET
    ).encode()
    
    addr_main = Address(
        payment_part=payment_hash,
        staking_part=stake_hash,
        network=Network.MAINNET
    ).encode()

    # 5) bech32 keys (warning: sk = sensitive!)
    pub_b32 = bech32_hrp_payload("ed25519_pk", pub32)
    sk_b32  = bech32_hrp_payload("ed25519_sk", seed32)

    # 6) Save files
    (OUT / "ed25519_seed.bin").write_bytes(seed32)
    (OUT / "ed25519_seed.hex").write_text(to_hex(seed32) + "\n")

    (OUT / "ed25519_pub.raw").write_bytes(pub32)
    (OUT / "ed25519_pub.hex").write_text(to_hex(pub32) + "\n")

    (OUT / "ed25519_keyhash.hex").write_text(to_hex(keyhash) + "\n")
    
    # Save stake key files (same as payment key)
    (OUT / "stake_seed.bin").write_bytes(stake_seed32)
    (OUT / "stake_seed.hex").write_text(to_hex(stake_seed32) + "\n")
    (OUT / "stake_pub.raw").write_bytes(stake_pub32)
    (OUT / "stake_pub.hex").write_text(to_hex(stake_pub32) + "\n")

    (OUT / "pkcs8.der").write_bytes(pkcs8_der)
    (OUT / "pkcs8.pem").write_bytes(pkcs8_pem)
    
    # Save priv.pem and pub.pem files
    (OUT / "priv.pem").write_bytes(pkcs8_pem)
    (OUT / "pub.pem").write_bytes(pub_pem)

    (OUT / "pkcs8.base64.txt").write_text(pkcs8_b64 + "\n")

    (OUT / "openssh_public.txt").write_text(openssh_pub + "\n")
    (OUT / "openssh_private.pem").write_bytes(openssh_priv)

    (OUT / "pubkey.bech32.txt").write_text(pub_b32 + "\n")
    (OUT / "secret.bech32.txt").write_text(sk_b32 + "\n")

    (OUT / "addr_test.txt").write_text(addr_test + "\n")
    (OUT / "addr_main.txt").write_text(addr_main + "\n")

    # Save private key as hex string
    sk_hex = to_hex(seed32)
    (OUT / "sk.txt").write_text(sk_hex + "\n")

    # 7) Short JSON for MeshJS/TypeScript
    summary = {
        "pubKeyHex": to_hex(pub32),
        "stakeKeyHex": to_hex(stake_pub32),
        "keyHashHex": to_hex(keyhash),
        "pkcs8Base64": pkcs8_b64,
        "pubKeyBech32": pub_b32,
        "addr_test": addr_test,
        "addr_main": addr_main,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    print("✅ Generated keys and artifacts:")
    print("   Note: Payment and stake keys are identical")
    print(f"   Private Key (hex): {sk_hex}")
    for f in [
        "ed25519_seed.bin","ed25519_seed.hex",
        "ed25519_pub.raw","ed25519_pub.hex",
        "ed25519_keyhash.hex",
        "stake_seed.bin","stake_seed.hex",
        "stake_pub.raw","stake_pub.hex",
        "pkcs8.der","pkcs8.pem","pkcs8.base64.txt",
        "priv.pem","pub.pem",
        "openssh_public.txt","openssh_private.pem",
        "pubkey.bech32.txt","secret.bech32.txt",
        "addr_test.txt","addr_main.txt",
        "sk.txt",
        "summary.json",
    ]:
        print("  ", f)

if __name__ == "__main__":
    main()

