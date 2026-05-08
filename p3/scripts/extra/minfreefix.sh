#!/bin/bash
# name: minfreefix
# version: 1.0
# description: minfreefix_desc
# icon: preload.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy
# optimized-only: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
free_mem_fix
zeninf "$rebootmsg" # while immediate rebooting is not necessary it is ideal