#!/bin/bash
# name: MangoJuice
# version: 1.0
# description: mgjuice_desc
# icon: mangojuice

# --- Start of the script code ---
_packages=(mangohud) && _install_
unset _packages
flatpak_in_lib
flatpak install --or-update --user --noninteractive com.valvesoftware.Steam.VulkanLayer.MangoHud/x86_64/stable org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/24.08
flatpak install --or-update --user --noninteractive io.github.radiolamp.mangojuice