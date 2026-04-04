#!/bin/bash
# name: Shader Booster
# version: 1.0
# description: sboost_desc
# icon: gaming.svg
# reboot: yes
# nocontainer
# optimized-only: yes

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/optimizers.lib"
if [ ! -f ${HOME}/.booster ]; then
    sboost_lib
else
    zenwrn "System already patched."
    exit 10
fi
