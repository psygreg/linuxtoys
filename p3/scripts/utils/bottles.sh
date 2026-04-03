#!/bin/bash
# name: Bottles
# version: 1.0
# description: bottles_desc
# icon: bottles.svg
# repo: https://usebottles.com

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    com.usebottles.bottles
)
_flatpak_