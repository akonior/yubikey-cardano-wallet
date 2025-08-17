PKCS11=/opt/homebrew/lib/libykcs11.dylib

mkdir -p build

ykman piv keys import --management-key 010203040506070801020304050607080102030405060708 --touch-policy always --pin-policy always 9c generated/keys/priv.pem

yubico-piv-tool -a verify-pin -P 123456

yubico-piv-tool -a verify-pin -P 123456 \
                -a selfsign-certificate -s 9c \
                -S "/CN=PIV-KEY/" \
                -i generated/keys/pub.pem -o build/cert.pem

yubico-piv-tool -a import-certificate -s 9c -i build/cert.pem

# HASH_HEX="$1"
# echo "$HASH_HEX" | xxd -r -p > build/msg.bin
# wc -c build/msg.bin   # should be 32

# pkcs11-tool \
#   --module "$PKCS11" \
#   --login --pin 123456 \
#   --sign --mechanism EDDSA \
#   --id 02 \
#   --input-file build/msg.bin \
#   --output-file build/sig.bin

#   xxd -p build/sig.bin | tr -d '\n'; echo