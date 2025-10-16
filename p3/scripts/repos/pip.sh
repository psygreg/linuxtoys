#!/bin/bash
# name: Pip
# version: 1.0
# description: pip_desc
# icon: pip.svg
# repo: https://pypi.org/project/pip/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
pip_lib
zeninf "$msg018"