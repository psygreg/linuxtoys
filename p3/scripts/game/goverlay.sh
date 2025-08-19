#!/bin/bash
# name: GOverlay
# version: 1.0
# description: goverlay_desc
# icon: goverlay

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
_packages=(mangohud goverlay) && _install_
unset _packages
if command -v flatpak &> /dev/null; then
    flatpak_in_lib
    flatpak install --or-update --user --noninteractive flathub com.valvesoftware.Steam.VulkanLayer.MangoHud/x86_64/stable org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08
fi