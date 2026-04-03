#!/bin/bash
# name: Postman
# version: 1.0
# description: postman_desc
# icon: postman.svg
# repo: https://www.postman.com

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    com.getpostman.Postman
)
_flatpak_
zeninf "$msg018"