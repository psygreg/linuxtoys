#!/bin/bash
# name: modsign
# version: 1.0
# description: modsign_desc
# icon: sign.svg
# compat: ostree, fedora, rhel
# reboot: yes
# nocontainer
# repo: https://github.com/CheariX/silverblue-akmods-keys
# new

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

rhel_check () {
    local major minor
    IFS="." read -r major minor <<< "${REDHAT_SUPPORT_PRODUCT_VERSION}"
    echo "$major.$minor"
    if (( major < 10 )) || (( major == 10 && minor < 0 )); then
        echo "Kernel module signing not supported in this version of the OS. Please update to RHEL/AlmaLinux 10."
        exit 100
    else
        return 0
    fi
}

{ is_rhel && rhel_check; } || true
sudo_rq
if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
    if is_ostree; then
        if ! rpm -qi "akmods-keys" &>/dev/null; then
            pkg_install rpmdevtools akmods
            sudo kmodgenca
            sudo mokutil --import /etc/pki/akmods/certs/public_key.der
            prep_tmp
            git clone https://github.com/CheariX/silverblue-akmods-keys
            cd silverblue-akmods-keys
            sudo bash setup.sh
            pkg_fromfile akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
        fi
    elif is_fedora || is_rhel; then
        pkg_install kmodtool akmods mokutil openssl
        sudo kmodgenca -a
        sudo mokutil --import /etc/pki/akmods/certs/public_key.der # displays enroll MOK prompt on reboot
    fi
fi
zeninf "$msg036"