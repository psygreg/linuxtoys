#!/bin/bash
# name: Minecraft Bedrock Launcher
# version: 1.0
# description: mcbe_desc
# icon: minecraft.svg
# repo: https://minecraft-linux.github.io

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub io.mrarm.mcpelauncher
