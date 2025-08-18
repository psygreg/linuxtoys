#!/bin/bash
# name: psaver
# version: 1.0
# description: psaver_desc
# icon: power-saver
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/optimizers.lib"
. /etc/os-release
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    sudo_rq
    psave_lib
else
    nonfatal "$msg234"
fi