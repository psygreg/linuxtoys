#!/bin/bash
# NAME: Audacity
# VERSION: 1.0
# DESCRIPTION: audacity_desc
# icon: audacity.svg
# repo: https://www.audacityteam.org/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    org.audacityteam.Audacity
)
_flatpak_
