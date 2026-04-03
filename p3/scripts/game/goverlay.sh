#!/bin/bash
# name: GOverlay
# version: 1.0
# description: goverlay_desc
# icon: goverlay.svg
# repo: https://github.com/benjamimgois/goverlay

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
_packages=(mangohud goverlay) && _install_
if command -v flatpak &> /dev/null; then
    _flatpaks=(
        com.valvesoftware.Steam.VulkanLayer.MangoHud
        org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 # lutris
        org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08
        org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/25.08
    )
    _flatpak_
fi