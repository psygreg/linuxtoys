#!/bin/bash
# name: Gear Lever
# version: 1.0
# description: glever_desc
# icon: gearlever.png
# repo: https://github.com/mijorus/gearlever

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    it.mijorus.gearlever
)
_flatpak_