#!/bin/bash
# name: Minecraft Bedrock Launcher
# version: 1.0
# description: mcbe_desc
# icon: minecraft

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.mrarm.mcpelauncher