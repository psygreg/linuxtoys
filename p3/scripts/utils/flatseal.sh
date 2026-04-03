#!/bin/bash
# name: Flatseal
# version: 1.0
# description: fseal_desc
# icon: flatseal.svg
# repo: https://github.com/tchx84/Flatseal

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    com.github.tchx84.Flatseal
)
_flatpak_