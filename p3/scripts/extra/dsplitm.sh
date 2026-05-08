#!/bin/bash
# name: dsplitm
# version: 1.0
# description: dsplitm_desc
# icon: utils.svg
# compat: ubuntu, debian, suse, fedora, arch, cachy
# reboot: yes
# nocontainer
# optimized-only: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    dsplitm_lib
else
    nonfatal "$msg234"
fi