#!/bin/bash
# name: Insomnia
# version: 1.0
# description: insomnia_desc
# icon: insomnia.svg
# repo: https://insomnia.rest/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    rest.insomnia.Insomnia
)
_flatpak_
zeninf "$msg018"