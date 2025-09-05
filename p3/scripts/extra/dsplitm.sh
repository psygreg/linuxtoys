#!/bin/bash
# name: dsplitm
# version: 1.0
# description: dsplitm_desc
# icon: utils.svg
# compat: ubuntu, debian, suse, fedora, arch, cachy
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/optimizers.lib"
sudo_rq
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    dsplitm_lib
else
    nonfatal $"This system has already been optimized by LinuxToys. To re-apply, please use the 'Undo Optimizations' script first."
fi