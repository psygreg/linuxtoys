#!/bin/bash
# name: Bazaar
# version: 1.0
# description: bazaar_desc
# icon: bazaar.svg
# repo: https://github.com/kolunmi/bazaar

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    io.github.kolunmi.Bazaar
)
_flatpak_
zeninf "$msg018"