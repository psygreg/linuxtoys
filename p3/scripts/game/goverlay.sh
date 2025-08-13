#!/bin/bash
# name: GOverlay
# version: 1.0
# description: goverlay_desc

# --- Start of the script code ---
_packages=(mangohud goverlay) && _install_
unset _packages
if command -v flatpak &> /dev/null; then
    flatpak_in_lib
    flatpak install --or-update --user --noninteractive com.valvesoftware.Steam.VulkanLayer.MangoHud/x86_64/stable org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08
fi