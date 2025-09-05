#!/bin/bash
# name: GeForce NOW
# version: 1.0
# description: gfn_desc
# icon: nvidia

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.freedesktop.Sdk//24.08
flatpak remote-add --user --if-not-exists GeForceNOW https://international.download.nvidia.com/GFNLinux/flatpak/geforcenow.flatpakrepo
flatpak install --or-update --user --noninteractive GeForceNOW com.nvidia.geforcenow
flatpak override --user --nosocket=wayland com.nvidia.geforcenow