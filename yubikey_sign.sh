#!/bin/bash
HASH_HEX="$1"

# Function to get PIN using pinentry
get_pin() {
    local pin
    if command -v pinentry-mac >/dev/null 2>&1; then
        # macOS GUI pinentry
        pin=$(echo -e "SETDESC YubiKey PIN required for signing\nSETPROMPT PIN:\nGETPIN\n" | pinentry-mac 2>/dev/null | grep "^D " | cut -d' ' -f2-)
    elif command -v pinentry-gtk2 >/dev/null 2>&1; then
        # GTK GUI pinentry
        pin=$(echo -e "SETDESC YubiKey PIN required for signing\nSETPROMPT PIN:\nGETPIN\n" | pinentry-gtk2 2>/dev/null | grep "^D " | cut -d' ' -f2-)
    elif command -v pinentry-qt >/dev/null 2>&1; then
        # Qt GUI pinentry
        pin=$(echo -e "SETDESC YubiKey PIN required for signing\nSETPROMPT PIN:\nGETPIN\n" | pinentry-qt 2>/dev/null | grep "^D " | cut -d' ' -f2-)
    elif command -v pinentry >/dev/null 2>&1; then
        # Default pinentry (usually terminal-based)
        pin=$(echo -e "SETDESC YubiKey PIN required for signing\nSETPROMPT PIN:\nGETPIN\n" | pinentry 2>/dev/null | grep "^D " | cut -d' ' -f2-)
    else
        echo "Error: No pinentry program found. Please install pinentry." >&2
        exit 1
    fi
    
    if [ -z "$pin" ]; then
        echo "Error: PIN entry cancelled or failed." >&2
        exit 1
    fi
    
    echo "$pin"
}

# Get PIN securely
PIN=$(get_pin)

# Sign with YubiKey using the provided PIN
echo "$HASH_HEX" | xxd -r -p | pkcs11-tool \
  --module /opt/homebrew/lib/libykcs11.dylib \
  --login \
  --pin "$PIN" \
  --sign --mechanism EDDSA \
  --id 02 \
  2>/dev/null \
  | xxd -p | tr -d '\n'
