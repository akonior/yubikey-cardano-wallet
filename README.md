# yubikey-cardano-wallet

## Cardano + YubiKey PoC

This repository contains a **proof of concept** showing how to use a YubiKey as a Cardano wallet.  
It demonstrates the full flow from key generation to signing and broadcasting a transaction.

### Steps

1. **Generate a Cardano Ed25519 key bundle**  
  ```bash
  python gen_cardano_ed25519_bundle.py
  ```
2. **Load the generated keys onto the YubiKey (PIV/EdDSA)**
```bash
./yubikey_load_keys.sh
```
3. **Run the full flow**
Create and sign a transaction that sends 1 tADA from the test account back to itself.
```bash
python e2e_test.py
```

⚠️ Before running, make sure to fund the generated test account with some tADA on the Cardano testnet.