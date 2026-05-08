#!/bin/bash
# name: Sunshine
# version: 1.0
# description: sunshine_desc
# icon: sunshine.png
# repo: https://github.com/LizardByte/Sunshine

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat dev.lizardbyte.app.Sunshine
sudo_rq
if is_nvidia; then
    if is_ubuntu; then
        pkg_install ca-certificates gnupg2
        curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
            && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
        sudo apt update
        pkg_install nvidia-container-toolkit nvidia-container-toolkit-base libnvidia-container-toolslibnvidia-container1
    else
        pkg_install nvidia-container-toolkit
    fi
    if is_solus; then
        pkg_install nvidia-vaapi-driver
    fi
fi
sudo flatpak run --command=additional-install.sh dev.lizardbyte.app.Sunshine