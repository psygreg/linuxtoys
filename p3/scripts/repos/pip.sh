#!/bin/bash
# name: Pip
# version: 1.0
# description: pip_desc
# icon: pip.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
pip_lib
zeninf $"Operations completed."