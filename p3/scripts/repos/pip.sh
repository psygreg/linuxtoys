#!/bin/bash
# name: Pip
# version: 1.0
# description: pip_desc
# icon: pip.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
sudo_rq
_packages=(pip)
_install_
zeninf "$msg018"