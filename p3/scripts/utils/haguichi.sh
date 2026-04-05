#!/bin/bash
# name: Haguichi
# version: 1.0
# description: haguichi_desc
# icon: haguichi.svg
# repo: https://github.com/ztefn/haguichi

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    com.github.ztefn.haguichi
)
_flatpak_