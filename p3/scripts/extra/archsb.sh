#!/bin/bash
# name: archsb
# version: 1.0
# description: archsb_desc
# compat: arch, cachy
# reboot: yes
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
zenwrn "$msg304"
sudo_rq
_packages=(sbctl efibootmgr)
_install_
sleep 1
if [ "$(sbctl status | grep -i 'secure boot' | grep -i 'disabled')" ]; then
    if [ "$(sbctl status | grep -i 'setup mode' | grep -i 'enabled')" ]; then
        # added procedure for grub in CA mode
        if command -v grub-install &>/dev/null; then
            sudo grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=GRUB --modules="tpm" --disable-shim-lock
        fi
        # create and enroll keys with sbctl
        sudo sbctl create-keys
        sudo sbctl enroll-keys -m -f
        # Sign all unsigned files
        while IFS= read -r line; do
            if [[ "$line" =~ ✗ ]]; then
                file=$(echo "$line" | awk '{print $2}')
                echo "Signing: $file"
                sudo sbctl sign -s "$file"
            fi
        done < <(sudo sbctl verify)
        
        echo "All files signed. Verifying..."
        sudo sbctl verify
        zeninf "$msg301"
        exit 0
    else
        fatal "$msg302"
    fi
else
    zeninf "$msg303"
    exit 100
fi