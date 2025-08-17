"""An example that demonstrates low-level construction of a transaction."""

import subprocess
import argparse
from blockfrost import BlockFrostApi, ApiError
from pycardano import (
    PaymentSigningKey,
    PaymentVerificationKey,
    Transaction,
    TransactionBody,
    TransactionInput,
    TransactionOutput,
    TransactionWitnessSet,
    VerificationKeyWitness,
)

# Helper function to load files
def load_key_file(filename):
    return open(f"generated/keys/{filename}").read().strip()

# Parse command line arguments
parser = argparse.ArgumentParser(description='Create and optionally submit a Cardano transaction')
parser.add_argument('--submit', action='store_true', 
                    help='Submit the transaction to the network (default: only create and sign)')
args = parser.parse_args()

print(f"Mode: {'SUBMIT' if args.submit else 'CREATE ONLY'}")
print("-" * 50)

# Load address and create signing key using helper function
addr = load_key_file("addr_test.txt")
# sk = PaymentSigningKey.from_primitive(bytes.fromhex(load_key_file("ed25519_seed.hex")))

# Initialize Blockfrost API for Preview network
API_KEY = "previewrb9rbzdsSkvObWVlqH5n29hwwnLLpyuw"
api = BlockFrostApi(project_id=API_KEY, base_url="https://cardano-preview.blockfrost.io/api/")

# Fetch UTXOs from Blockfrost
print(f"Fetching UTXOs for address: {addr}")
try:
    utxos = api.address_utxos(addr)
    
    if not utxos:
        print("No UTXOs found for this address. Please send some test ADA first.")
        exit(1)
    
    # Find the largest UTXO
    largest_utxo = max(utxos, key=lambda x: int(x.amount[0].quantity))
    
    print(f"Found {len(utxos)} UTXOs")
    print(f"Using UTXO: {largest_utxo.tx_hash}#{largest_utxo.output_index}")
    print(f"Amount: {int(largest_utxo.amount[0].quantity) / 1_000_000} ADA")
    
    # Create transaction input from the fetched UTXO
    tx_in = TransactionInput.from_primitive([largest_utxo.tx_hash, largest_utxo.output_index])
    
    # Calculate amounts
    total_input = int(largest_utxo.amount[0].quantity)  # in lovelace
    send_amount = 1_000_000  # 1 ADA in lovelace
    fee = 200_000  # estimated fee in lovelace
    change_amount = total_input - send_amount - fee
    
    print(f"Total input: {total_input / 1_000_000} ADA")
    print(f"Sending: {send_amount / 1_000_000} ADA")
    print(f"Fee: {fee / 1_000_000} ADA")
    print(f"Change: {change_amount / 1_000_000} ADA")
    
    # Define transaction outputs - send 1 ADA to same address, rest as change
    output1 = TransactionOutput.from_primitive([addr, send_amount])  # 1 ADA
    output2 = TransactionOutput.from_primitive([addr, change_amount])  # change
    
except ApiError as e:
    print(f"Blockfrost API error: {e}")
    exit(1)

# Create a transaction body from inputs and outputs
tx_body = TransactionBody(inputs=[tx_in], outputs=[output1, output2], fee=fee)

# Print the signing key in hex format
# print("Signing key hex:", sk.payload.hex())

# Load verification key from generated public key file
pub_key_hex = load_key_file("ed25519_pub.hex")
vk = PaymentVerificationKey.from_primitive(bytes.fromhex(pub_key_hex))
# Print the verification key in hex format
print("Verification key hex:", vk.payload.hex())


# Sign the transaction body hash
# signature = sk.sign(tx_body.hash())
# Print the transaction body hash
print("Transaction body hash:", tx_body.hash().hex())

# print("\033[31m" + signature.hex() + "\033[0m")

# Sign with YubiKey
print("Signing with YubiKey...")
try:
    result = subprocess.run(
        ["./yubikey_sign.sh", tx_body.hash().hex()],
        capture_output=True,
        text=True,
        check=True
    )
    signature2_hex = result.stdout.strip()
    signature2 = bytes.fromhex(signature2_hex)
    print("YubiKey signature:", "\033[32m" + signature2_hex + "\033[0m")
except subprocess.CalledProcessError as e:
    print(f"Error calling yubikey_sign.sh: {e}")
    print(f"stderr: {e.stderr}")
    signature2 = None

# Add verification key and the signature to the witness set
vk_witnesses = [VerificationKeyWitness(vk, signature2)]

# Create final signed transaction
signed_tx = Transaction(tx_body, TransactionWitnessSet(vkey_witnesses=vk_witnesses))

# Convert transaction to CBOR
tx_cbor = signed_tx.to_cbor()
print(f"Transaction CBOR length: {len(tx_cbor)} bytes")
print(f"Transaction CBOR hex: {tx_cbor.hex()}")

# Submit transaction only if --submit flag is provided
if args.submit:
    print("\nSubmitting transaction to Cardano testnet...")
    try:
        # Save CBOR to temporary file (Blockfrost expects file path)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.cbor') as tmp_file:
            tmp_file.write(tx_cbor)
            tmp_file_path = tmp_file.name
        
        # Submit transaction
        tx_hash = api.transaction_submit(tmp_file_path)
        
        # Clean up temporary file
        import os
        os.unlink(tmp_file_path)
        
        print(f"\n✅ Transaction successful!")
        print(f"Transaction hash: {tx_hash}")
        print(f"🔗 View on CardanoScan: https://preview.cardanoscan.io/transaction/{tx_hash}")
    except ApiError as e:
        print(f"\n❌ Transaction failed: {e}")
        print("This might be due to insufficient funds, incorrect fee, or other validation errors.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
else:
    print(f"\n📝 Transaction created and signed successfully!")
    print(f"💡 To submit to network, run: python {__file__} --submit")
    print(f"🔗 Transaction ready for submission")