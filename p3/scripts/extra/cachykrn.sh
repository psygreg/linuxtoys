#!/bin/bash
# name: CachyOS Kernel
# description: cachykrn_desc
# icon: cachyos.svg
# compat: fedora
# reboot: yes

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

sudo_rq
sudo dnf copr enable bieszczaders/kernel-cachyos
pkg_install kernel-cachyos kernel-cachyos-devel-matched
sudo setsebool -P domain_kernel_load_modules on
# ensure it boots with the cachyos kernel as default, remaining with the standard Fedora kernel as backup option
pkg_install grubby
prep_create /etc/kernel/postinst.d/99-default
sudo tee /etc/kernel/postinst.d/99-default > /dev/null << 'EOF'
#!/bin/sh

set -e

grubby --set-default=/boot/$(ls /boot | grep vmlinuz.*cachy | sort -V | tail -1)
EOF
sudo chown root:root /etc/kernel/postinst.d/99-default ; sudo chmod u+rx /etc/kernel/postinst.d/99-default
# secure boot handling
if sudo mokutil --sb-state 2>/dev/null | grep -qE "(SecureBoot enabled|Platform is in Setup Mode)"; then
    INSTALLED_KERNEL=$(ls /boot | grep vmlinuz.*cachy | sort -V | tail -1)
    prep_dir /etc/mok && cd /etc/mok
    sudo openssl req -new -x509 -newkey rsa:2048 \
        -keyout MOK.priv \
        -outform DER -out MOK.der \
        -nodes -days 36500 \
        -subj "/CN=Custom Kernel Signing Key/"
    sudo openssl x509 -in MOK.der -inform DER -out MOK.pem
    sudo chmod 600 MOK.priv
    sudo chmod 644 MOK.pem MOK.der
    sudo mokutil --import /etc/mok/MOK.der
    sudo sbsign \
        --key /etc/mok/MOK.priv \
        --cert /etc/mok/MOK.pem \
        --output "/boot/vmlinuz-$INSTALLED_KERNEL" \
        "/boot/vmlinuz-$INSTALLED_KERNEL"
    # automate future signings
    prep_create /etc/kernel/install.d/90-sbsign.install
    sudo tee /etc/kernel/install.d/90-sbsign.install > /dev/null << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

COMMAND="$1"
KERNEL_VERSION="$2"
BOOT_DIR="$3"

KEY="/etc/mok/MOK.priv"
CERT="/etc/mok/MOK.pem"

# Only act on kernel install
[[ "$COMMAND" == "add" ]] || exit 0

KERNEL_IMAGE="$BOOT_DIR/vmlinuz-$KERNEL_VERSION"

if [[ -f "$KERNEL_IMAGE" ]]; then
    echo "Signing kernel: $KERNEL_IMAGE"

    TMP="$(mktemp)"

    sbsign \
        --key "$KEY" \
        --cert "$CERT" \
        --output "$TMP" \
        "$KERNEL_IMAGE"

    mv "$TMP" "$KERNEL_IMAGE"
fi
EOF
    sudo chmod +x /etc/kernel/install.d/90-sbsign.install
fi
zeninf "$rebootmsg"