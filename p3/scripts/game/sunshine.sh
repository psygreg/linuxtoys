#!/bin/bash
# name: Sunshine
# version: 1.0
# description: sunshine_desc
# icon: sunshine.png
# repo: https://github.com/LizardByte/Sunshine

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    dev.lizardbyte.app.Sunshine
)
_flatpak_
sudo_rq
if is_nvidia; then
    _packages=(nvidia-container-toolkit)
    if is_solus; then
        _packages+=(nvidia-vaapi-driver)
    fi
    _install_
fi
sudo flatpak run --command=additional-install.sh dev.lizardbyte.app.Sunshine