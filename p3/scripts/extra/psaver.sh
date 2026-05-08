#!/bin/bash
# name: psaver
# version: 1.0
# description: psaver_desc
# icon: psaver.svg
# reboot: yes
# nocontainer
# repo: https://thealexdev23.github.io/power-options/
# optimized-only: yes
# compat: !cachy

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    sudo_rq
    psave_lib
else
    nonfatal "$msg234"
fi