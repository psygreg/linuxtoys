#!/bin/bash
# name: Shader Booster
# version: 1.0
# description: sboost_desc
# icon: gaming.svg
# reboot: yes
# nocontainer
# optimized-only: yes
# compat: !solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
if [ ! -f ${HOME}/.booster ]; then
    sboost_lib
else
    zenwrn "System already patched."
    exit 100
fi
