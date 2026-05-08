#!/bin/bash
# name: GeForce NOW
# version: 1.0
# description: gfn_desc
# icon: nvidia.svg
# repo: https://geforcenow.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat org.freedesktop.Sdk//24.08
flatpak remote-add --system --if-not-exists GeForceNOW https://international.download.nvidia.com/GFNLinux/flatpak/geforcenow.flatpakrepo
flatpak install --or-update --system --noninteractive GeForceNOW com.nvidia.geforcenow
flatpak override --system --nosocket=wayland com.nvidia.geforcenow