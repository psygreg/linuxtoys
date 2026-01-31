#!/bin/bash
# name: hwaccel-flatpak
# version: 1.0
# description: hwaccel-flatpak_desc
# icon: flathub.svg
# repo: https://freedesktop-sdk.gitlab.io/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
sudo_rq
flatpak_in_lib
hwaccel_flat_lib
zeninf "$msg018"