#!/bin/bash
# name: Cohesion
# version: 1.0
# description: cohesion_desc
# icon: cohesion.svg
# repo: https://github.com/brunofin/cohesion

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    io.github.brunofin.Cohesion
)
_flatpak_