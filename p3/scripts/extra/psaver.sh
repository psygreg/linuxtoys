#!/bin/bash
# name: psaver
# version: 1.0
# description: psaver_desc
# icon: psaver.svg
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/optimizers.lib"
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    sudo_rq
    psave_lib
else
    nonfatal $"This system has already been optimized by LinuxToys. To re-apply, please use the 'Undo Optimizations' script first."
fi